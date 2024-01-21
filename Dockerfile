ARG PYTHON_VERSION=3.12-alpine3.19
FROM python:${PYTHON_VERSION} 

WORKDIR /app

COPY . . 

RUN apk add --no-cache \
  build-base~=0.5 \
  font-roboto-mono~=3.000 \
  git~=2.43 \
  linux-headers~=6.5 \
  python3-tkinter~=3.11.6 \
  && pip3 install --no-cache-dir -r requirements.txt \
  && mv tsr /usr/local/bin \
  && chmod +x /usr/local/bin/tsr

CMD ["tsr"]

