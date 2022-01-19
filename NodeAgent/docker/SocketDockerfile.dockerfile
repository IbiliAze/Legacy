FROM python:3.9

ARG SRC_DIR=/app/

ENV PORT 16243

RUN mkdir -p $SRC_DIR

ADD server.py $SRC_DIR
ADD setup.py $SRC_DIR
ADD .env $SRC_DIR
ADD README.md $SRC_DIR
ADD requirements.txt $SRC_DIR
ADD utils/ $SRC_DIR/utils
ADD certs/ $SRC_DIR/certs
ADD log/ $SRC_DIR/log

WORKDIR $SRC_DIR

RUN pip install -r requirements.txt

EXPOSE $PORT

# ENTRYPOINT [ "server" ]
ENTRYPOINT [ "python3" ]
CMD [ "server.py" ]
