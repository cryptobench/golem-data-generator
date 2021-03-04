FROM python:3.8.7-slim
VOLUME /golem/input /golem/output
RUN apt update
RUN apt install -y imagemagick
RUN apt install -y athena-jot 
RUN apt install -y zip
COPY generate_data.sh /golem/entrypoint/
COPY directions.txt /golem/entrypoint/
COPY admin_images/ /golem/entrypoint/admin_images/
WORKDIR /golem/entrypoint
