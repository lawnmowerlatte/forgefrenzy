FROM public.ecr.aws/lambda/python:3.9 as forgefrenzy

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
COPY docker/lambda/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY src/forgefrenzy ${LAMBDA_TASK_ROOT}/forgefrenzy

LABEL package=forgefrenzy.gateway

FROM forgefrenzy as handler
CMD [ "forgefrenzy.gateway.lambda.handler" ]

FROM forgefrenzy as admin
CMD [ "forgefrenzy.gateway.lambda.admin" ]
