# SplitShare

SplitShare рассчитывает общие расходы друзей, долю каждого участника и переводы для погашения задолженности. Суммы хранятся в целых копейках, поэтому расчёт сохраняет каждую копейку.

## Запуск

Python 3.9 или новее. Внешних Python-зависимостей нет.

```bash
python3 app/splitshare.py examples/weekend.json --format text
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 scripts/smoke.py
python3 dist/splitshare.pyz examples/weekend.json --format text
```

Без `--format text` программа возвращает JSON. Для примера с ужином и такси Вика возвращает Ане 1300 рублей, Борис — 400 рублей.

## Документация и разработка

- [Wiki](https://github.com/eductionnn-netizen/splitshare/wiki)
- [Задачи](https://github.com/eductionnn-netizen/splitshare/issues)
- [Доска](https://github.com/users/eductionnn-netizen/projects/1/views/1)
- [Roadmap](https://github.com/users/eductionnn-netizen/projects/1/views/4)
- [Квартальный план и зависимости](https://github.com/eductionnn-netizen/splitshare/wiki/Quarter%E2%80%90plan)
- [Организация CI](ci/README.md)

Текущая версия — консольное приложение для одной группы в рублях. Веб-интерфейс, аккаунты, постоянное хранилище и подтверждение возвратов описаны в плане дальнейшего развития. Программа предлагает переводы и не выполняет банковских операций.

## Доступ

Основной репозиторий и Project публичные. MrDeryf имеет право записи в основной репозиторий. Локальный runner зарегистрирован только в отдельном приватном `splitshare-ci`; основной репозиторий не назначает ему задания.
