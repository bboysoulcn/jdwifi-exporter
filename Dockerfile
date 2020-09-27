FROM python:3
WORKDIR /jd
COPY jd .
RUN pip install -r /jd/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY docker-entrypoint.sh /usr/local/bin/
RUN ln -s /usr/local/bin/docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]