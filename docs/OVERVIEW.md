```markdown
---

1. تصویر کلی سیستم

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


---

2. لایه Input

کاربر می‌تواند از چند جا وارد شود:

USER
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
      Web           Mobile       Telegram
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
                 AI Gateway

در آینده می‌توان Desktop و حتی Wake Word هم اضافه کرد.


---

3. Open WebUI

Open WebUI نقش Interface را دارد.

یعنی:

Chat

Conversation

Markdown rendering

Code blocks

Tables

Images

Links

Voice input

Voice playback


اما نباید TTS logic را داخل خود Open WebUI پیچیده کنیم.

Open WebUI فقط باید بداند:

AI Response
     ↓
Display

و در صورت نیاز:

Audio Job
     ↓
Poll / Event
     ↓
Play Audio


---

4. LiteLLM

LiteLLM در معماری تو فقط مسئول LLM Gateway است.

Open WebUI
     ↓
LiteLLM
     ↓
Gemma / Llama / Other Model

مثلاً:

http://172.20.48.2:4000

LiteLLM نباید مسئول:

Redis

TTS

RustFS

FFmpeg

Voice cloning


باشد.

این separation خیلی مهم است.


---

5. LLM Response

LLM یک Response کامل تولید می‌کند.

مثلاً:

برای حل مشکل Nginx باید configuration را تغییر دهید.

```nginx
location /api {
    proxy_pass http://backend:8000;
}

مستندات کامل را می‌توانید اینجا ببینید:

https://nginx.org/

این Response **نباید تغییر کند**.

چون Open WebUI باید همان Markdown کامل را نمایش دهد.

---

# 6. Response Processor

اینجا یکی از مهم‌ترین بخش‌های معماری توست.

```text
                Full AI Response
                       │
                       ▼
              Response Processor
                       │
          ┌────────────┼────────────┐
          │            │            │
       Markdown      Language     Speech
         Parser      Detector     Policy

به جای اینکه با Regex ساده متن را پاک کنیم، بهتر است Markdown را parse کنیم.

مثلاً:

{
  "blocks": [
    {
      "type": "text",
      "text": "برای حل مشکل Nginx باید configuration را تغییر دهید."
    },
    {
      "type": "code",
      "language": "nginx",
      "content": "location /api {...}"
    },
    {
      "type": "link",
      "url": "https://nginx.org/"
    }
  ]
}


---

7. Speech Policy

بعد این blocks تبدیل می‌شوند به Speech Blocks.

مثلاً:

speech_policy:

  text:
    speak: true

  heading:
    speak: true

  code:
    speak: false
    announcement: true

  link:
    speak: false
    announcement: true

  table:
    speak: false
    announcement: true

  image:
    speak: false
    announcement: true

  quote:
    speak: true

  math:
    speak: false
    announcement: true


---

8. نتیجه TTS

مثلاً AI گفته:

برای حل مشکل Nginx باید configuration را تغییر دهید.

[CODE]

مستندات:

[LINK]

TTS نباید این را بخواند:

location slash api...
proxy pass...
https colon slash slash...

بلکه:

برای حل مشکل Nginx باید configuration را تغییر دهید.

اینجا configuration مربوط به Nginx را قرار داده‌ام.

مستندات مرتبط را هم در ادامه قرار داده‌ام.

و UI همچنان Code و Link واقعی را نمایش می‌دهد.


---

9. دو Voice مختلف

من این بخش را حتماً نگه می‌دارم.

Main Voice

صدای Clone شده‌ی تو:

Ali Voice

برای:

Normal AI response

System / Announcement Voice

یک صدای دیگر:

System Voice

برای:

"Here is the code."
"I've included the link below."
"The details are shown in the table."

در فارسی:

«کد مربوطه را در ادامه قرار داده‌ام.»

«لینک مربوطه در ادامه آمده است.»

«جزئیات در جدول زیر نمایش داده شده است.»

این باعث می‌شود کاربر سریع بفهمد:

> الان AI دارد صحبت می‌کند یا دارد یک عنصر UI را معرفی می‌کند.




---

10. Language Detection

بعد از Semantic Processing باید زبان مشخص شود.

Speech Text
     │
     ▼
Language Detector
     │
     ├── fa
     ├── en
     ├── ru
     ├── tr
     └── ...

مثلاً:

{
  "language": "fa-IR"
}

یا:

{
  "language": "en-US"
}


---

11. Language Router

اینجا تصمیم می‌گیریم چه TTS Engine استفاده شود.

Language Router
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
      EN              FA              RU
       │               │               │
       ▼               ▼               ▼
 Chatterbox       Persian TTS      Chatterbox

این خیلی بهتر از این است که یک TTS را مجبور کنیم تمام زبان‌ها را انجام دهد.


---

12. فارسی

برای فارسی مسئله فقط Voice Clone نیست.

سه چیز داریم:

Voice Identity
      +
Persian Pronunciation
      +
Persian Prosody

یعنی مدل باید:

فارسی را درست تلفظ کند

تکیه‌ها را درست بگذارد

ریتم فارسی داشته باشد

جمله‌بندی طبیعی داشته باشد

اصطلاحات انگلیسی داخل فارسی را درست بخواند


برای همین می‌توانیم یک Persian TTS Engine جدا داشته باشیم و حتی نسخه fine-tuned فارسی را benchmark کنیم.


---

13. Voice Profile

برای هر زبان reference voice جدا نگه می‌داریم.

مثلاً:

RustFS
│
└── voices/
    │
    └── ali/
        │
        ├── en/
        │   └── reference.wav
        │
        ├── fa/
        │   └── reference.wav
        │
        └── ru/
            └── reference.wav

یعنی اگر صدای فارسی تو خیلی بهتر از انگلیسی‌ات باشد، مدل فارسی reference خودش را دارد.


---

14. Persian Text Normalizer

این قسمت برای پروژه تو خیلی مهم است.

قبل از TTS:

LLM Text
   ↓
Persian Normalizer
   ↓
TTS Text

مثلاً:

Nginx

نباید الزاماً به شکل انگلیسی خوانده شود.

Dictionary می‌تواند داشته باشیم:

pronunciation:

  Nginx: "اِن‌جین‌اِکس"
  Docker: "داکر"
  Kubernetes: "کوبِرنِتِیز"
  PostgreSQL: "پُستگرِس"
  Redis: "رِدیس"
  API: "اِی‌پی‌آی"
  SSH: "اِس‌اِس‌اِچ"
  HTTP: "اِچ‌تی‌تی‌پی"

این Dictionary می‌تواند per-language باشد.


---

15. TTS Gateway

بعد از preprocessing:

Speech Representation
        │
        ▼
   TTS Gateway
        │
        ▼
   Redis Stream

مثلاً:

tts:generate


---

16. چرا Redis؟

چون تو همین الان Redis داری.

برای این workload نیازی نیست Kafka اضافه کنیم.

Redis Streams:

tts:generate

و Consumer Group:

tts-workers

Worker:

TTS Worker #1

در آینده:

TTS Worker #1
TTS Worker #2
TTS Worker #3

اما برای RTX 4060 تو من فعلاً:

concurrency = 1

می‌گذارم.

یعنی GPU زیر فشار شدید نمی‌رود.


---

17. TTS Job

هر Job مثلاً:

{
  "job_id": "tts_123",
  "conversation_id": "conv_456",
  "message_id": "msg_789",

  "language": "fa-IR",

  "voice_id": "ali-fa",
  "announcement_voice_id": "system-fa",

  "text": "برای حل این مشکل باید تنظیمات Nginx را تغییر دهید.",

  "format": "mp3",

  "status": "queued"
}


---

18. Job Lifecycle

queued
  │
  ▼
processing
  │
  ├──────────────┐
  ▼              ▼
completed       failed
  │              │
  ▼              ▼
RustFS          retry

Redis باید metadata و queue را نگه دارد.

Audio binary را داخل Redis نمی‌گذاریم.


---

19. TTS Worker

Worker:

Redis
  │
  ▼
TTS Worker
  │
  ├── Load Voice
  │
  ├── Select Model
  │
  ├── Generate WAV
  │
  ├── FFmpeg
  │
  └── Upload RustFS

روی لپ‌تاپ تو:

RTX 4060 8GB

و چون مدل دیگری هم GPU را مصرف می‌کند:

TTS concurrency = 1


---

20. Audio Pipeline

من این pipeline را پیشنهاد می‌کنم:

TTS Model
    │
    ▼
   WAV
    │
    ▼
  FFmpeg
    │
    ├───────────────┐
    ▼               ▼
   MP3             Opus
    │               │
    ▼               ▼
 RustFS          Telegram

WAV برای intermediate خوب است.

اما storage اصلی:

MP3

و برای Telegram Voice:

Opus


---

21. RustFS

RustFS برای Object Storage:

ai-audio/
│
├── conversations/
│   │
│   └── {conversation_id}/
│       │
│       └── {message_id}/
│           ├── audio.mp3
│           └── audio.opus
│
└── voices/
    │
    └── ali/
        ├── en/
        ├── fa/
        └── ru/

Redis فقط می‌گوید:

audio_url = ...

خود فایل داخل RustFS است.


---

22. Open WebUI

بعد از completion:

TTS Worker
     │
     ▼
RustFS
     │
     ▼
TTS Result
     │
     ▼
Open WebUI
     │
     ▼
🔊 Play

برای asynchronous بودن می‌توانیم:

POST /tts/jobs

بزنیم و فوراً:

{
  "job_id": "tts_123",
  "status": "queued"
}

بگیریم.

بعد:

GET /tts/jobs/tts_123

و وقتی:

{
  "status": "completed",
  "audio_url": "..."
}

شد، audio پخش شود.


---

23. Streaming لازم نیست

با توجه به چیزی که گفتی، برای تو TTS real-time اولویت ندارد.

یعنی:

LLM Response
      ↓
Immediately show text
      ↓
Queue TTS
      ↓
30 sec / 1 min later
      ↓
Audio ready

این اتفاق کاملاً acceptable است.

حتی می‌توانیم TTS را به paragraph تقسیم کنیم:

Paragraph 1 → Job 1
Paragraph 2 → Job 2
Paragraph 3 → Job 3

و audioها به ترتیب آماده شوند.

این بعداً امکان progressive playback می‌دهد.


---

24. Telegram

Telegram می‌تواند یک Adapter جدا باشد:

AI
 │
 ▼
Speech Pipeline
 │
 ▼
RustFS
 │
 ▼
Telegram Adapter
 │
 ├── MP3 → sendAudio
 │
 └── Opus → voice message

بنابراین Telegram نباید مستقیماً به TTS Engine وصل شود.


---

25. کل معماری نهایی

در نهایت چیزی که من برای پروژه تو می‌سازم این است:

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


---

26. سرویس‌های اصلی

پس در implementation نهایی تقریباً این components را داریم:

Service	وظیفه

Open WebUI	UI / Chat / Voice
LiteLLM	LLM Gateway
Gemma/Llama	Local LLM
Response Processor	تبدیل AI Response به Speech Representation
Language Detector	تشخیص زبان
Persian Normalizer	بهینه‌سازی متن فارسی برای TTS
TTS Gateway	ساخت Job
Redis Streams	Queue
TTS Worker	اجرای TTS
Chatterbox	EN/RU/etc.
Persian TTS	فارسی
FFmpeg	Audio conversion
RustFS	Object Storage
Telegram Adapter	ارسال Voice/Audio



---

27. چیزی که در نهایت به دست می‌آوری

این دیگر صرفاً:

> Text → Speech



نیست.

بلکه تبدیل می‌شود به:

> AI Response → Semantic Presentation → Multilingual Voice → Async Audio Pipeline



و این قسمت به نظرم مهم‌ترین بخش پروژه توست.

مثلاً AI می‌گوید:

> برای رفع مشکل، ابتدا سرویس Docker را restart کنید. سپس configuration را بررسی کنید.



بعد code هم دارد، table هم دارد، link هم دارد.

کاربر روی UI می‌بیند:

برای رفع مشکل، ابتدا سرویس Docker را restart کنید.

┌──────────────────────────┐
│ docker compose restart   │
└──────────────────────────┘

[configuration table]

Documentation:
https://...

ولی Voice فقط می‌گوید:

> «برای رفع مشکل، ابتدا سرویس Docker را restart کنید.
دستور مربوط به Docker را در ادامه قرار داده‌ام.
جزئیات configuration هم در جدول زیر آمده است.
لینک مستندات را نیز در ادامه می‌توانید ببینید.»



و اگر متن فارسی باشد:

fa
 ↓
Persian TTS
 ↓
Ali Persian Voice

اگر انگلیسی:

en
 ↓
Chatterbox
 ↓
Ali English Voice

اگر روسی:

ru
 ↓
Chatterbox
 ↓
Ali Russian Voice


---

یک اصل معماری که من برای کل پروژه حفظ می‌کنم

LLM هیچ‌وقت نباید بداند که قرار است متنش چگونه به Voice تبدیل شود.

LLM فقط:

Generate the best answer.

و بعد:

Response Processor
        ↓
Presentation Layer
        ↓
TTS Layer
        ↓
Queue
        ↓
Worker
        ↓
Storage

این separation باعث می‌شود بعداً بتوانی بدون تغییر LLM، TTS engine را عوض کنی، زبان فارسی را با یک مدل بهتر جایگزین کنی، Voice Clone جدید اضافه کنی، Telegram را اضافه کنی، یا حتی یک روز ElevenLabs/XTTS/Chatterbox/مدل دیگری را جایگزین کنی.

این را من به‌عنوان baseline معماری نهایی Voice Assistant تو در نظر می‌گیرم.
```
