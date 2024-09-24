from urllib import request


def api_healthcheck(is_spexodisks_com: bool = False, use_8000: bool = True):
    if is_spexodisks_com:
        host_str = 'https://spexodisks.com'
    else:
        host_str = 'http://localhost'
    port = ''
    if use_8000:
        port = ':8000'
    request.urlopen(f'{host_str}{port}/api/stats_total/?format=json')


if __name__ == "__main__":
    api_healthcheck()
