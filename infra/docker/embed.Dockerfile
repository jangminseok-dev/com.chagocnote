# 임베딩 프로세스 — 뜻 검색(⑨)의 벡터를 만든다. 토치 없이 ONNX 런타임(CPU).
# 모델 파일은 이미지를 지을 때 공개 저장소에서 받아 이미지에 넣는다 — 기동 때 인터넷이 필요 없다.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/embed
COPY embed/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# intfloat/multilingual-e5-small (MIT, 384차원). 판을 고정한다 — 판이 바뀌면 벡터가 달라져 다시 색인해야 한다.
ARG MODEL_REPO=intfloat/multilingual-e5-small
ARG MODEL_REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3
RUN python -c "from huggingface_hub import hf_hub_download as g; [g('${MODEL_REPO}', f, revision='${MODEL_REVISION}', local_dir='/models/e5-small') for f in ('onnx/model.onnx', 'onnx/tokenizer.json')]"
COPY embed /srv/embed
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100", "--no-access-log"]
