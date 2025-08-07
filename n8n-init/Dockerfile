# n8n-init/Dockerfile
FROM docker:latest
RUN apk add --no-cache bash
COPY update-workflows.sh /update-workflows.sh
RUN chmod +x /update-workflows.sh
CMD ["/update-workflows.sh"]