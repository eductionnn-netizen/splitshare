import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app.web import make_server, Store


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "groups.sqlite3"
        self.server = make_server(0, self.path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, method=None, headers=None):
        request = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                          method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def group(self):
        status, result = self.request("/api/groups", {"name": "Trip", "members": ["Anna", "Boris", "Vika"]})
        self.assertEqual(status, 201)
        return result

    def expense(self, **changes):
        return {"id": "request-1", "title": "Dinner", "date": "2026-10-23", "payer": "Anna",
                "amount_kopecks": 100, "participants": ["Anna", "Boris", "Vika"], **changes}

    def test_add_rounding_and_persistence(self):
        group = self.group()
        status, result = self.request(f"/api/groups/{group['id']}/expenses", self.expense())
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["shares_kopecks"], {"Anna": 34, "Boris": 33, "Vika": 33})
        self.assertEqual(Store(self.path).get(group["id"])["expenses"], result["expenses"])

    def test_duplicate_submission_and_conflicting_id(self):
        path = f"/api/groups/{self.group()['id']}/expenses"
        self.request(path, self.expense())
        status, result = self.request(path, self.expense())
        self.assertEqual(status, 200)
        self.assertEqual(result["total_kopecks"], 100)
        self.assertEqual(len(result["expenses"]), 1)
        self.assertEqual(self.request(path, self.expense(amount_kopecks=200))[0], 400)

    def test_delete_recalculates_balances(self):
        path = f"/api/groups/{self.group()['id']}/expenses"
        self.request(path, self.expense())
        status, result = self.request(path + "/request-1", method="DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(result["total_kopecks"], 0)
        self.assertEqual(result["result"]["transfers"], [])
        self.assertEqual(self.request(path + "/request-1", method="DELETE")[0], 404)

    def test_invalid_expenses_do_not_change_group(self):
        path = f"/api/groups/{self.group()['id']}"
        for change in [{"amount_kopecks": True}, {"amount_kopecks": 1.1}, {"amount_kopecks": 0},
                       {"amount_kopecks": 10**12}, {"participants": []}, {"payer": "Ivan"},
                       {"participants": ["Anna", "Anna"]}, {"date": "2026-02-30"}, {"title": " "}]:
            with self.subTest(change=change):
                self.assertEqual(self.request(path + "/expenses", self.expense(**change))[0], 400)
        self.assertEqual(self.request(path)[1]["expenses"], [])

    def test_group_validation(self):
        for members in [["Anna"], ["Anna", " Anna "], ["Anna", " "], "Anna", list(map(str, range(21)))]:
            self.assertEqual(self.request("/api/groups", {"name": "Trip", "members": members})[0], 400)
        self.assertEqual(self.request("/api/groups", {"name": " ", "members": ["Anna", "Boris"]})[0], 400)
        self.assertEqual(self.request("/api/groups")[1], [])

    def test_groups_are_independent(self):
        first, second = self.group(), self.group()
        self.request(f"/api/groups/{first['id']}/expenses", self.expense())
        self.assertEqual(self.request(f"/api/groups/{second['id']}")[1]["expenses"], [])
        self.assertEqual(len(self.request("/api/groups")[1]), 2)

    def test_foreign_origin_and_host_rejected(self):
        data = {"name": "Trip", "members": ["Anna", "Boris"]}
        self.assertEqual(self.request("/api/groups", data, headers={"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request("/api/groups", headers={"Host": "example.com"})[0], 403)
        self.assertEqual(self.request("/api/groups")[1], [])

    def test_missing_group_and_path(self):
        self.assertEqual(self.request("/api/groups/absent")[0], 404)
        self.assertEqual(self.request("/../web.py")[0], 404)

    def test_static_assets(self):
        for path, marker in [("/", b"SplitShare"), ("/app.js", b"selectGroup"), ("/style.css", b"@media")]:
            with urlopen(self.base + path, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(marker, response.read())
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
