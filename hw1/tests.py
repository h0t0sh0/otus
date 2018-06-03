import unittest
import json
import log_analyzer
import os
import datetime
import time
import shutil
import hashlib


class LogAnalyzerTest(unittest.TestCase):
    def testUpdateConfig(self):
        salt = int(time.mktime(datetime.datetime.now().timetuple()))
        config = {'param1': 'value1',
                  'param2': 'value2',
                  'param3': 'value3',
                  'CONFIG_DIR': '.'}
        config_file = "/tmp/testconfigfile" + str(salt)
        config_file_data = {'param2': 'valueNew2',
                            'param4': 'valueNew4',
                            'param5': 'valueNew5'}
        result = {'CONFIG_DIR': '.',
                  'param1': 'value1',
                  'param2': 'valueNew2',
                  'param3': 'value3',
                  'param4': 'valueNew4',
                  'param5': 'valueNew5'}

        with open(config_file, 'w') as f:
            f.write(json.dumps(config_file_data))
        testresult, code, message = log_analyzer.update_config(config_file, config)
        self.assertEqual(result, testresult)

        config_file_data = {}
        with open(config_file, 'w') as f:
            f.write(json.dumps(config_file_data))
        testresult, code, message = log_analyzer.update_config(config_file, config)
        self.assertEqual(config, testresult)

        os.remove(config_file)
        testresult, code, message = log_analyzer.update_config(config_file, config)
        self.assertNotEqual(code, 0)

    def testGetLastLog(self):
        salt = int(time.mktime(datetime.datetime.now().timetuple()))
        work_dir = '/tmp/some_work_dir' + str(salt)
        report_dir = '/tmp/some_report_dir' + str(salt)
        os.makedirs(work_dir)
        os.makedirs(report_dir)
        files = ['nginx-access-ui.log-20180601.txt',
                 'nginx-access-ui.log-20180304',
                 'nginx-access-ui.log-20180629.gz',
                 'nginx-access-ui.log-20180701',
                 'nginx-access-ui.log-20180702.bz2']
        for f in files:
            os.system("touch {}".format(os.path.join(work_dir, f)))

        log_file, report_file = log_analyzer.get_log_and_report_names(work_dir,
                                                                      report_dir)

        self.assertEqual(os.path.join(work_dir, files[3]), log_file)
        self.assertEqual(os.path.join(report_dir, 'report-2018.07.01.html'), report_file)

        os.remove(os.path.join(work_dir, files[3]))
        log_file, report_file = log_analyzer.get_log_and_report_names(work_dir,
                                                                      report_dir)
        self.assertEqual(os.path.join(work_dir, files[2]), log_file)
        self.assertEqual(os.path.join(report_dir, 'report-2018.06.29.html'), report_file)

        os.remove(os.path.join(work_dir, files[2]))
        log_file, report_file = log_analyzer.get_log_and_report_names(work_dir,
                                                                      report_dir)
        self.assertEqual(os.path.join(work_dir, files[0]), log_file)
        self.assertEqual(os.path.join(report_dir, 'report-2018.06.01.html'), report_file)

        shutil.rmtree(work_dir)
        shutil.rmtree(report_dir)

    def testAlreadyParsed(self):
        salt = int(time.mktime(datetime.datetime.now().timetuple()))
        work_dir = "/tmp/some_work_dir" + str(salt)
        report_dir = "/tmp/some_report_dir" + str(salt)
        log_name = "nginx-access-ui.log-20180304"
        report_name = "report-2018.03.04.html"

        log_file = os.path.join(work_dir, log_name)
        report_file = os.path.join(report_dir, report_name)

        result = log_analyzer.already_parsed(log_file, report_file)
        self.assertFalse(result)

        os.makedirs(work_dir)
        os.makedirs(report_dir)

        with open(log_file, "w") as f:
            f.write("some log")

        result = log_analyzer.already_parsed(log_file, report_file)
        self.assertFalse(result)

        m = hashlib.md5()
        m.update("success" + report_file.encode("utf-8"))

        with open(report_file, "w") as f:
            f.write("some data\n")
            f.write("\n<!-- d8e8fca2dc0f896fd7cb4cb0031ba249 -->\n".encode("utf-8"))

        result = log_analyzer.already_parsed(log_file, report_file)
        self.assertFalse(result)

        with open(report_file, "w") as f:
            f.write("some data\n")
            f.write("\n<!-- {} -->\n".format(m.hexdigest()).encode("utf-8"))

        result = log_analyzer.already_parsed(log_file, report_file)
        self.assertTrue(result)

        shutil.rmtree(work_dir)
        shutil.rmtree(report_dir)

    def testPercentage(self):
        p = log_analyzer.percentage(41, 100)
        self.assertAlmostEqual(p, 41, places=2)

        p = log_analyzer.percentage(22.2, 100)
        self.assertAlmostEqual(p, 22.2, places=2)

    def testMedian(self):
        t = [1, 1, 2, 3]
        median = log_analyzer.median(t)
        self.assertAlmostEqual(median, 1.5, places=2)

        t = [1, 2, 3]
        median = log_analyzer.median(t)
        self.assertAlmostEqual(median, 2, places=2)

        t = [1.1, 2.2, 2.3, 3.8]
        median = log_analyzer.median(t)
        self.assertAlmostEqual(median, 2.25, places=2)


if __name__ == '__main__':
    unittest.main()
