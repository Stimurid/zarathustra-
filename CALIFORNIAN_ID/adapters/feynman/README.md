# Feynman Adapter (contract only)

Реальный API-контракт Feynman (Abulafia / ModerBober) в локальных
материалах не найден. Этот файл — точная спецификация интеграции, а не
фиктивная реализация. Реализуй binding, когда получишь access.

## Требуемый интерфейс host → runtime

```python
class FeynmanBinding:
    def receive_utterance(self, meta, text) -> None: ...
    def request_council(self, mode="fast", context=None) -> PipelineResult: ...
    def stream_intermediate_events(self, callback) -> None: ...
    def commit_review(self, review_decision) -> None: ...
```

## Требуемый интерфейс runtime → host

- Отправлять только `render_user_response` (не raw turns).
- Отправлять `security_events` как host-уведомления.
- Не пробрасывать raw prompts.
- Уважать `review_gate`: host принимает решения review, не runtime.

## Что НЕ надо делать в этой сборке

- Не выдумывать endpoints и headers.
- Не создавать mock Feynman API, который выглядит как реальный.
- Не превращать generic_host adapter в feynman-specific.
