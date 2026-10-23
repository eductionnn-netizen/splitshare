# SplitShare

SplitShare рассчитывает общие расходы друзей, долю каждого участника и переводы для погашения задолженности. Суммы хранятся в целых копейках, поэтому расчёт сохраняет каждую копейку.

## Запуск приложения

Нужен Python 3.9 или новее. Дополнительные пакеты устанавливать не требуется.

На macOS откройте файл **Start SplitShare.command** в папке проекта. Приложение
откроется в браузере по адресу **http://127.0.0.1:8787**. Для остановки сервера
нажмите Control+C в открывшемся окне терминала.

Запуск из терминала:

```bash
python3 -m app.web --database .local-data/splitshare.sqlite3 --port 8787 --open
```

В интерфейсе можно создать группу, добавить расходы, выбрать плательщика и участников,
посмотреть балансы и предлагаемые переводы. Ошибочный расход можно удалить.
Кнопка «Выгрузить JSON» сохраняет данные выбранной группы в файл.

Группы и расходы сохраняются в SQLite. При указанной выше команде база находится
в `.local-data/splitshare.sqlite3` и сохраняется после закрытия браузера или перезапуска.
Если параметр `--database` не указан, используется `~/.splitshare/splitshare.sqlite3`.
Для резервной копии остановите сервер и скопируйте файл базы.

Приложение предназначено для работы на одном компьютере. Сервер принимает подключения
только с `127.0.0.1`. Аккаунты, совместный доступ через интернет и подтверждение возвратов
запланированы отдельно. Программа рассчитывает суммы и не выполняет банковских операций.

## Тесты и сборка

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 scripts/smoke.py
python3 dist/splitshare-web.pyz --port 8787 --open
```

Сборка создаёт два архива: `splitshare-web.pyz` с интерфейсом и `splitshare.pyz`
для работы с JSON из командной строки. Проверка `smoke.py` запускает оба архива,
проверяет веб-страницу, API, расчёт и сохранение расходов во временной базе.

## Работа с JSON

```bash
python3 app/splitshare.py examples/weekend.json --format text
```

Без `--format text` результат выводится в JSON. Для примера с ужином и такси
Вика возвращает Ане 1300 рублей, Борис — 400 рублей.

## Документация и разработка

- [Wiki](https://github.com/eductionnn-netizen/splitshare/wiki)
- [Задачи](https://github.com/eductionnn-netizen/splitshare/issues)
- [Доска](https://github.com/users/eductionnn-netizen/projects/1/views/1)
- [Задачи и подзадачи](https://github.com/users/eductionnn-netizen/projects/1/views/6)
- [Roadmap](https://github.com/users/eductionnn-netizen/projects/1/views/4)
- [Квартальный план и зависимости](https://github.com/eductionnn-netizen/splitshare/wiki/Quarter%E2%80%90plan)
- [Организация CI](ci/README.md)

## Доступ

Основной репозиторий и Project публичные. MrDeryf имеет право записи в основной репозиторий. Локальный runner зарегистрирован только в отдельном приватном `splitshare-ci`; основной репозиторий не назначает ему задания.
