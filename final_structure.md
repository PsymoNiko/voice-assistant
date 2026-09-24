                           ┌──────────────────────┐
                           │         USER         │
                           └──────────┬───────────┘
                                      │
                   ┌──────────────────┼──────────────────┐
                   │                  │                  │
                   ▼                  ▼                  ▼
                OpenWebUI          Mobile            Telegram
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      ▼
                               ┌──────────────┐
                               │   Gateway    │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │    LiteLLM   │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │ Gemma/Llama  │
                               └──────┬───────┘
                                      │
                              Full Markdown
                                      │
                                      ▼
                       ┌─────────────────────────┐
                       │ Response Processor      │
                       │                         │
                       │ Markdown AST            │
                       │ Language Detection      │
                       │ Speech Policy            │
                       │ Persian Normalizer      │
                       └────────────┬────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
             Original Response                 Speech Text
                    │                               │
                    ▼                               ▼
               OpenWebUI                       TTS Gateway
                                                    │
                                                    ▼
                                              Redis Streams
                                                    │
                                                    ▼
                                              TTS Worker
                                                    │
                                                    ▼
                                            Language Router
                                                    │
                           ┌────────────────────────┼────────────────────┐
                           │                        │                    │
                           ▼                        ▼                    ▼
                          EN                       FA                   RU
                           │                        │                    │
                      Chatterbox              Persian TTS           Chatterbox
                           │                   fine-tuned                │
                           └────────────────────────┼────────────────────┘
                                                    │
                                                    ▼
                                                 FFmpeg
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │                               │
                                    ▼                               ▼
                                   MP3                             Opus
                                    │                               │
                                    ▼                               ▼
                                  RustFS                        Telegram
                                    │
                                    ▼
                              Audio URL/Event
                                    │
                                    ▼
                                OpenWebUI
                                    │
                                    ▼
                                  🔊