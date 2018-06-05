# Python Developer course. 2018-05
Homeworks.

### Homework_1 Log Analazer

Log Analazer - это парсер логов веб сервиса. Парсер ищет в директории логов последний лог файл, парсит его и генерирует отчет в виде html файла, в котором содержится:

* `count` - сколько раз встречается URL, абсолютное значение
* `count_perc` - сколько раз встречается URL, в процентах относительно `count`
* `time_sum` - суммарное время запросов для данного URL'a, абсолютное значение
* `time_perc` - суммарное время запросов для данного URL'a, в процентах от `time_sum`
* `time_avg` - среденее время запроса для данного URL
* `time_max` - максимальное время запроса для данного URL
* `time_med` - медиана времен запроса для данного URL


***Использование***
```
python2.7 log_analazer.py [--config config_file]
```

***Пример конфиг файла(формат: json)***
```json
{
    "REPORT_SIZE": 100,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./logs",
    "SCRIPT_LOG": "log_analyzer.log",
    "SCRIPT_LOG_LEVEL": "INFO",
    "ERRORS_THRESHOLD_%": 10
}
```

* `REPORT_SIZE` - число URL-ов c наибольшим `time_sum`
* `REPORT_DIR` - директория, куда будут складываться отчеты
* `LOG_DIR` - директория, где расположены лог файлы
* `SCRIPT_LOG` - имя лога работы Log Analazer
* `SCRIPT_LOG_LEVEL` - уровень логирования
* `ERRORS_THRESHOLD_%` - порог ошибок парсинга в процентах, при котором скрипт завершит свою работу досрочно


***Запуск тестов***
```
cd hw1
python -m unittest discover -v
testAlreadyParsed (tests.LogAnalyzerTest) ... ok
testGetLastLog (tests.LogAnalyzerTest) ... ok
testMedian (tests.LogAnalyzerTest) ... ok
testPercentage (tests.LogAnalyzerTest) ... ok
testUpdateConfig (tests.LogAnalyzerTest) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.046s

OK
```
