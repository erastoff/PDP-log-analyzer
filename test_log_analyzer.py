import unittest
import pandas as pd


from log_analyzer import (
    parse_log_line,
    create_dataframe,
)


class TestParser(unittest.TestCase):
    def test_parse_log_line(self):
        log_line = '1.99.174.176 3b81f63526fa8  - [30/Jun/2017:03:28:22 +0300] "GET /api/1/photogenic_banners/list/?server_name=WIN7RB1 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498782502-32900793-4707-10488736" "-" 0.134'
        result = parse_log_line(log_line)
        expected_result = (
            "1.99.174.176",
            "3b81f63526fa8",
            "-",
            "30/Jun/2017:03:28:22 +0300",
            "GET",
            "/api/1/photogenic_banners/list/?server_name=WIN7RB1",
            "HTTP/1.1",
            "200",
            "12",
            "-",
            "Python-urllib/2.7",
            "-",
            "1498782502-32900793-4707-10488736",
            '"-"',
            "0.134",
        )
        self.assertEqual(result, expected_result)

    def test_create_dataframe(self):
        log_lines = [
            '1.2.2.4 3b81f63526fa8  - [30/Jun/2017:03:28:22 +0300] "GET /api/1/ HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498782502-32900793-4707-10488736" "-" 0.134',
            '5.6.7.8 3b81f63526fa8  - [30/Jun/2017:03:28:22 +0300] "GET /api/2/ HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498782502-32900793-4707-10488736" "-" 0.134',
        ]
        result = create_dataframe(log_lines)
        expected_result = pd.DataFrame(
            {
                "$request_path": ["/api/1/", "/api/2/"],
                "count": [1, 1],
                "count_perc": [50.0, 50.0],
                "time_sum": [0.134, 0.134],
                "time_perc": [50.0, 50.00],
                "time_avg": [0.134, 0.134],
                "time_max": [0.134, 0.134],
                "time_med": [0.134, 0.134],
            }
        ).set_index(["$request_path"])
        self.assertTrue(result.equals(expected_result))


if __name__ == "__main__":
    unittest.main()
