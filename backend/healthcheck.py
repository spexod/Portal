from urllib import request


def api_healthcheck():
    request.urlopen("localhost:8000/api/stats_total/?format=json")


if __name__ == "__main__":
    api_healthcheck()
