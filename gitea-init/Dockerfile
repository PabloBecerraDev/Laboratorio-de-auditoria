FROM alpine:3.20

RUN apk add --no-cache docker-cli curl jq git bash

COPY init-gitea.sh /opt/init-gitea.sh
RUN chmod +x /opt/init-gitea.sh

ENTRYPOINT ["/opt/init-gitea.sh"]
