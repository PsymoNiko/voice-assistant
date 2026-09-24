                         ┌─────────────────────┐
                         │       USER          │
                         │                     │
                         │ Web / Mobile /      │
                         │ Desktop / Telegram  │
                         └──────────┬──────────┘
                                    │
                          Text / Voice Input
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Open WebUI       │
                         │                     │
                         │ Chat / Voice / UI   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      LiteLLM        │
                         │    AI Gateway       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Local LLM         │
                         │                     │
                         │ Gemma / Llama       │
                         └──────────┬──────────┘
                                    │
                             Full AI Response
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │    Response Processor       │
                    │                              │
                    │ Markdown AST                 │
                    │ Semantic extraction           │
                    │ Language detection            │
                    │ TTS policy                    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
             Original Response              Speech Response
                    │                             │
                    ▼                             ▼
              Open WebUI                    TTS Gateway
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
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                          ▼                       ▼                       ▼
                         EN                      FA                      RU
                          │                       │                       │
                    Chatterbox             Persian TTS             Chatterbox
                    / clone                 fine-tuned              / clone
                          │                       │                       │
                          └───────────────────────┼───────────────────────┘
                                                  │
                                                  ▼
                                             FFmpeg
                                                  │
                                  ┌───────────────┴──────────────┐
                                  │                              │
                                  ▼                              ▼
                                MP3                            Opus
                                  │                              │
                                  ▼                              ▼
                               RustFS                        Telegram