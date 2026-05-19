---
name: ticnote-api
description: |
  TicNote API integration: API Key instructions, token authentication, file upload, and knowledge-base project listing.
  Triggers:
  - "ticnote", "TicNote"
  - "ticnote token"
  - "upload to ticnote"

---

## TicNote API 

### Overview 

| Item               | Value                         |
| ------------------ | ----------------------------- |
| **Authentication** | Bearer Token                  |
| **Token validity** | 24 hours                      |
| **Request format** | JSON, except for file uploads |

Look for credentials in a `TICNOTE_APPKEY` environment variable outside the skill, then in a local `.env` file. If not found, prompt the user to input the AppKey.

TICNOTE_URL=https://api.ticnote.com/v1 # Optional base URL


### Obtaining Bearer Token 
To use the TicNote API, you need to obtain an API key and generate a Bearer token. Follow these steps:

**Endpoint:** `POST /api/p1/appkey/login`

Log in with the AppKey to obtain a Bearer Token. No additional authentication is required.

```bash
curl -X POST <BASE_URL>/api/p1/appkey/login \
  -H "Content-Type: application/json" \
  -d '{"appkey": "<YOUR_APPKEY>"}'
```

**Example response:**

```json
{
  "code": 0,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "firstLogin": false,
    "tokenType": "Bearer"
  }
}
```

**Later requests must include this header: `Authorization: Bearer <token>`**

Execution:

```bash
python ${SKILL_PATH}/scripts/get_token.py --appkey "<APPKEY>"
```

**Example error response:**

```json
{
  "code": 11865,
  "msg": "Appkey not found"
}
```

When the endpoint returns a non-zero `code`, the request failed. Report the `msg` value to the user and include the detailed explanation:

| code  | msg                                      | Explanation                                                                                                                                                                                                                                                                                                                                                            |
| ----- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 11865 | Appkey not found                         | The AppKey is invalid or does not exist. Check: 1. whether the AppKey is spelled correctly and complete, starting with `tnovs_sk_`, `tnovs_sit_sk_`, `tncn_sk_`, or `tncn_sit_sk_`; 2. whether the AppKey was successfully obtained from TicNote; 3. if the AppKey looks correct but still fails, contact an administrator to confirm whether it was deleted or reset. |
| 11864 | User not found                           | The user linked to the AppKey does not exist. The account may have been deleted or may never have been registered. Confirm that the related account, such as email or phone number, is active.                                                                                                                                                                         |
| 11866 | Account associated with appkey not found | The account linked to the AppKey does not exist in the system. The account may have been deleted. Use a valid account to obtain a new AppKey.                                                                                                                                                                                                                          |
| 11867 | Appkey is disabled                       | The AppKey has been disabled and cannot be used to obtain a token. Contact an administrator to confirm the status of the AppKey.                                                                                                                                                                                                                                       |

## Workflow

Run the relevant operation based on the user's request:

1. **List knowledge-base projects** -> Use the token to call `/api/v2/file-index/chats` and retrieve the project/folder list.
2. **List files under a project** -> Use the token to call `GET /api/v1/file-index/file-tree?rootId={projectId}` and retrieve all files under the project.
3. **Upload file** -> Use the token to call the file upload flow in three steps: sign -> upload to COS -> register in the knowledge base.
4. **View file details / poll transcription** -> `GET /api/v2/file-index/file-detail/{recordId}`.
5. **Submit transcription task** -> `POST /api/v1/task/transcribe/commit`.
6. **Regenerate summary for audio** -> `POST /api/v1/task/resummary/commit`.
7. **Summarize file for non-audio** -> `POST /api/project/project/summary/local_file`.
8. **Translate** -> `POST /api/v1/translate`.
9. **Share file** -> `POST /api/share/{audio|localFile}`, then access with `GET /api/share/{shareType}/{shareCode}`.
10. **Generate podcast** -> `POST /api/podcast/generate`.
11. **Deep Research** -> `POST /api/v1/deep/research/query`.
12. **User settings** -> `GET/PUT /api/v1/user/setting`.
13. **Knowledge-base file management** -> Delete, rename, copy, and move.


### 1. List Knowledge-Base Projects/Folders

**Endpoint:** `GET /api/v2/file-index/chats`

Get the current user's knowledge-base project/folder list. Supports fuzzy search by name. 

Project "System Notifications" is for internal use only and SHOULD NOT be displayed to users. Filter it out based on the `project_name` field. 

**Request parameters:**

| Parameter | Type   | Required | Description                                       |
| --------- | ------ | -------- | ------------------------------------------------- |
| query     | string | No       | Search keyword for fuzzy matching by project name |

```bash
curl -X GET "<BASE_URL>/api/v2/file-index/chats?query=<KEYWORD>" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example response:**

```json
{
  "chats": [
    {
      "id": "chat_001",
      "name": "R&D Document Library",
      "type": "private_virtual",
      "chat_type": "virtual_employee",
      "is_group": false,
      "has_agent": true,
      "project_id": "10086",
      "project_name": "R&D Document Library",
      "projectInfo": {
        "id": "10086",
        "name": "R&D Document Library",
        "icon": "folder",
        "color": "#4A90D9",
        "recordType": 1,
        "fileNum": 42
      },
      "participants": [
        {
          "id": "1001",
          "name": "User A",
          "type": "human",
          "isCurrentUser": true,
          "role": "owner"
        }
      ],
      "agent_count": 1,
      "createdAt": "2026-01-15T08:00:00Z",
      "updatedAt": "2026-03-10T12:00:00Z",
      "lastMessageAt": "2026-03-12T09:30:00Z"
    }
  ]
}
```

**Response field notes:**

| Field                         | Description         |
| ----------------------------- | ------------------- |
| `chats[].name`                | Project/folder name |
| `chats[].projectInfo.fileNum` | File count          |

> Output rule: Display only **index, name, and file count**. Do not show internal fields such as `project_id` or `chat_type` to the user.

Execution:

```bash
python ${SKILL_PATH}/scripts/list_projects.py --token "<TOKEN>" --appkey "<APPKEY>" [--query "<KEYWORD>"]
```

### 2. List Files Under a Project

**Endpoint:** `GET /api/v1/file-index/file-tree`

Get all files under a specified project/folder and return a file tree.

Project "System Notifications" is for internal use only and should NOT be queried for file list information. 

**Request parameters (query):**

| Parameter | Type | Required | Description                                                     |
| --------- | ---- | -------- | --------------------------------------------------------------- |
| rootId    | long | Yes      | Project ID, meaning `project_id` from the project list endpoint |

```bash
curl -X GET "<BASE_URL>/api/v1/file-index/file-tree?rootId=<PROJECT_ID>" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example response:**

```json
{
  "success": true,
  "fileTree": [
    {
      "id": "2020733843988295682",
      "fileId": "2020733843988295681",
      "fileType": "agent_file",
      "name": "Xian Weather Push-2026-02-09.html",
      "type": "file",
      "path": "Xian Weather Push-2026-02-09.html",
      "subRemark": "{\"transcodeStatus\":\"suc\",\"notRead\":1,\"originSuffix\":\"agent_file\"}",
      "children": []
    }
  ]
}
```

**Response field notes:**

| Field                  | Description                                                                                                       |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `fileTree`             | File tree array                                                                                                   |
| `fileTree[].id`        | Record ID (`recordId`), used for file detail queries                                                              |
| `fileTree[].fileId`    | File ID                                                                                                           |
| `fileTree[].fileType`  | File type, such as `agent_file`, `upload_recording`, `recording_file`, `pdf`, `docx`, etc.                        |
| `fileTree[].name`      | File name                                                                                                         |
| `fileTree[].type`      | Node type: `file` or `directory`                                                                                  |
| `fileTree[].path`      | File path                                                                                                         |
| `fileTree[].subRemark` | Additional JSON information, including `transcodeStatus`, `summaryId`, `transcribeId`, `deepResearchStatus`, etc. |
| `fileTree[].children`  | Child nodes, included for directories                                                                             |

Execution:

```bash
python ${SKILL_PATH}/scripts/list_files.py --token "<TOKEN>" --appkey "<APPKEY>" --root-id "<PROJECT_ID>"
```

> Output rule: Display only **index and name**. Do not show internal fields such as `fileType` or `id` to the user.

### 3. Upload a File to the Knowledge Base

File upload has three steps: get signature -> PUT upload to COS -> register in the knowledge base.

**Directory selection flow:** When the user does not specify `parentId` (target directory):
1. First call the "List knowledge-base projects" endpoint (see section 3) and show the project list to the user.
2. If the user selects a project, use that `project_id` as `parentId` for the upload.
3. If the user does not select any project and asks to continue directly, upload with an empty `parentId` (the backend uploads it to the user's default directory).

**Summary confirmation before upload (important):** When the user requests a file upload, before executing the upload you must ask whether they want to trigger file summarization after upload:
- Example prompt: "Ready to upload xxx to the xxx project. After the upload finishes, should I also trigger file summarization?"
- If the user confirms that a summary is needed, automatically call the corresponding summary endpoint after upload (section 8 for audio, section 9 for non-audio) without asking again.
- If the user explicitly refuses, upload only and do not trigger a summary.
- If the user has not answered clearly, such as only saying "upload", ask before uploading. Do not skip this confirmation step.

**fileId confirmation mechanism (important):** After successful registration, the upload script automatically uses the file-list endpoint to confirm the real `fileId` and outputs the `confirmed_file_id` field. Later operations such as summarization and transcription **must use `confirmed_file_id`**, not the `fileId` returned directly by the registration endpoint, because they may differ.

Execution:

```bash
# Full upload with target directory specified
python ${SKILL_PATH}/scripts/upload_file.py --token "<TOKEN>" --appkey "<APPKEY>" --file "/path/to/file" --parent-id "<PROJECT_ID>"

# If no directory is specified, the script automatically lists projects and asks the user to choose
python ${SKILL_PATH}/scripts/upload_file.py --token "<TOKEN>" --appkey "<APPKEY>" --file "/path/to/file"
```

> Output rule: The project selection list should display only **index, name, and file count**. Do not show internal fields such as `project_id` to the user.

#### Step 1: Get COS Upload Signature

**Endpoint:** `GET /api/v1/tencent/oss/apply/token`

Use the backend signing service to obtain Tencent Cloud COS upload authorization. No local COS SDK installation is required.

> Frontend reference: `docs/ufile_tencent.js` -> `getUFileToken()`, `docs/UploadTool.ts` -> `_tokenUrl`

**Request parameters (query):**

| Parameter   | Type   | Required | Description                                                                               |
| ----------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| method      | string | Yes      | Must match the actual upload method: normal upload `PUT`, multipart initialization `POST` |
| bucket      | string | Yes      | COS bucket name, such as `tc-nj-ticnote-1324023246`                                       |
| key         | string | Yes      | Full file path in COS, automatically URL encoded                                          |
| content_md5 | string | No       | File content MD5, calculated by frontend SparkMD5; can be empty                           |
| contentType | string | No       | File MIME type, such as `audio/wav` or `application/pdf`                                  |
| date        | string | No       | Can be empty                                                                              |

```bash
curl -X GET "<BASE_URL>/api/v1/tencent/oss/apply/token?method=PUT&bucket=tc-nj-ticnote-1324023246&key=ticnote-web-prd%2F2026-03%2Fabc123def456.pdf&content_md5=&contentType=application/pdf&date=" \
  -H "Authorization: Bearer <TOKEN>"
```

**Response:** JSON format. The signature is in `.data` for normal uploads or `.auth` for multipart uploads.

#### Step 2: PUT Upload File to Tencent Cloud COS

Use the signature returned from step 1 to upload the file directly to COS via HTTP PUT. `cos-python-sdk-v5` is not required.

> Frontend reference: `docs/ufile_tencent.js` -> `uploadFile()`

**COS upload URL:** `https://{bucket}.cos.{region}.myqcloud.com/{key}`

**Request headers:**

| Header        | Description                                           |
| ------------- | ----------------------------------------------------- |
| Authorization | Signature string returned from step 1                 |
| Content-Type  | File MIME type                                        |
| Content-MD5   | File content MD5, matching the value used for signing |

```bash
curl -X PUT "https://{bucket}.cos.{region}.myqcloud.com/{key}" \
  -H "Authorization: <SIGNATURE_STRING>" \
  -H "Content-Type: application/pdf" \
  -H "Content-MD5: <FILE_MD5>" \
  --data-binary @file.pdf
```

**File storage path (key) rule:** `{env}/{YYYY-MM}/{uuid}.{ext}`
- `env`: Determined by AppKey. If the AppKey contains `sit`, use `ticnote-web-sit`; otherwise use `ticnote-web-prd`.
- `YYYY-MM`: Current year and month, such as `2026-03`.
- `uuid`: Randomly generated UUID, 32-character hex without hyphens.
- `ext`: File extension.

> Frontend reference: `docs/UploadTool.ts` -> `_joinFileName()` uses `genorateUuid()`.

**COS configuration, automatically selected by AppKey:**

| AppKey prefix | Region group | Bucket                      | Region             | CDN                                      |
| ------------- | ------------ | --------------------------- | ------------------ | ---------------------------------------- |
| `tncn_*`      | China        | `tc-nj-ticnote-1324023246`  | `ap-nanjing`       | `https://cdn.ticnote.cn`                 |
| `tnovs_*`     | Overseas     | `voice-recorder-1308581983` | `na-siliconvalley` | `https://voice-recorder-cdn.ticnote.com` |

> China sit/prd share the same bucket, and overseas sit/prd also share the same bucket. The env prefix (`ticnote-web-sit` / `ticnote-web-prd`) distinguishes file ownership.

**Supported file types:** PDF, TXT, DOC/DOCX, XLS/XLSX, PPT/PPTX, MD, CSV, HTML, MP3, WAV, MP4, images, etc.

#### Step 3: Register the File in the Knowledge Base

**Endpoint:** `POST /api/v1/knowledge/upload`

Register the CDN URL of the successfully uploaded COS file into the specified knowledge-base directory.

> Use the **CDN URL** (`{cdn_domain}/{key}`) during registration, matching the frontend `UploadTool.ts` behavior.

**Request parameters:**

| Parameter | Type | Location | Required | Description                                                                       |
| --------- | ---- | -------- | -------- | --------------------------------------------------------------------------------- |
| parentId  | long | query    | No       | Parent directory ID, meaning `project_id`; if empty, upload to the root directory |

**Request body (JSON array):**

```json
[
  {
    "fileName": "file-name.pdf",
    "fileType": "pdf",
    "fileUrl": "https://cdn.ticnote.cn/ticnote-web-prd/2026-03/uuid.pdf",
    "recordType": 1
  }
]
```

| Field      | Type   | Required | Description                                                  |
| ---------- | ------ | -------- | ------------------------------------------------------------ |
| fileName   | string | Yes      | File name, including extension                               |
| fileType   | string | Yes      | File type, meaning extension such as `pdf`, `docx`, or `mp3` |
| fileUrl    | string | Yes      | Full URL of the file in COS                                  |
| recordType | int    | No       | Record type                                                  |
| fileId     | long   | No       | File ID, used for existing files                             |
| recordTime | long   | No       | Recording timestamp for audio files                          |

```bash
curl -X POST "<BASE_URL>/api/v1/knowledge/upload?parentId=<PROJECT_ID>" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[{"fileName":"report.pdf","fileType":"pdf","fileUrl":"https://cdn.example.com/ticnote-web-prd/2026-03/abc123.pdf"}]'
```

**Example response:**

```json
{
  "code": 0,
  "data": {
    "totalCount": 1,
    "successCount": 1,
    "failedCount": 0,
    "successFiles": [
      {
        "recordId": 2031647298439811075,
        "fileId": 98765,
        "fileName": "report.pdf",
        "fileType": "pdf",
        "fileUrl": "https://cdn.ticnote.cn/ticnote-web-prd/2026-03/uuid.pdf",
        "status": 1,
        "type": 2
      }
    ],
    "failedFiles": []
  }
}
```

> **Critical field:** `successFiles[].recordId` is required for later file-detail queries and transcription status polling.

**successFiles field notes:**

| Field    | Description                                            |
| -------- | ------------------------------------------------------ |
| recordId | Knowledge-base record ID, used for file-detail queries |
| fileId   | File ID                                                |
| fileName | File name                                              |
| fileType | File type                                              |
| fileUrl  | File URL                                               |
| status   | Processing status; see status code table               |
| type     | File type: 0=recording directory, 1=directory, 2=file  |

**failedFiles field notes:**

| Field         | Description    |
| ------------- | -------------- |
| fileName      | File name      |
| fileType      | File type      |
| fileUrl       | File URL       |
| failureReason | Failure reason |
| errorCode     | Error code     |

### 4. View File Details / Poll Transcription Status

**Endpoint:** `GET /api/v2/file-index/file-detail/{recordId}`

Two usage scenarios:
1. **View file content** - Get detailed information for a single file, including transcript text, summary, metadata, etc.
2. **Poll transcription status** - After uploading an audio/video file, poll periodically until transcription finishes.

**Request parameters:**

| Parameter | Type | Location | Required | Description                                                             |
| --------- | ---- | -------- | -------- | ----------------------------------------------------------------------- |
| recordId  | long | path     | Yes      | Knowledge-base record ID from upload response `successFiles[].recordId` |

```bash
curl -X GET "<BASE_URL>/api/v2/file-index/file-detail/<RECORD_ID>" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example response for audio/video file:**

```json
{
  "code": 0,
  "data": {
    "recordId": 2031647298439811075,
    "fileId": 98765,
    "fileName": "meeting-recording.mp3",
    "title": "meeting-recording.mp3",
    "fileType": "mp3",
    "type": 2,
    "isVoice": true,
    "status": 2,
    "transcodeStatus": "suc",
    "fileUrl": "https://cdn.ticnote.cn/...",
    "formatUrl": "https://cdn.ticnote.cn/...",
    "duration": 3600,
    "language": "zh",
    "transcribeId": 123456,
    "transcribeJson": "{ ... transcript JSON ... }",
    "summaryId": 789012,
    "summaryJson": "{ ... summary JSON ... }",
    "dataVersion": "v2",
    "deepResearchStatus": 0,
    "updateTime": "2026-03-12T12:00:00Z",
    "owner": { "id": "1001", "name": "User A" }
  }
}
```

**Example response for document file:**

```json
{
  "code": 0,
  "data": {
    "recordId": 2031647298439811075,
    "fileId": 98765,
    "fileName": "report.pdf",
    "title": "report.pdf",
    "fileType": "pdf",
    "type": 2,
    "isVoice": false,
    "status": 2,
    "transcodeStatus": "suc",
    "fileUrl": "https://cdn.ticnote.cn/...",
    "transcribeJson": "{ ... file preview content ... }",
    "deepResearchStatus": 0,
    "updateTime": "2026-03-12T12:00:00Z",
    "owner": { "id": "1001", "name": "User A" }
  }
}
```

**Key field notes:**

| Field                | Description                                                                                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `recordId`           | Knowledge-base record ID                                                                                                                        |
| `fileId`             | File ID                                                                                                                                         |
| `isVoice`            | Whether the file is audio/video                                                                                                                 |
| `status`             | Processing status; see status code table below                                                                                                  |
| `transcodeStatus`    | Transcoding status; see status code table below                                                                                                 |
| `transcribeJson`     | Transcript/preview content as a JSON string                                                                                                     |
| `summaryJson`        | Summary content as a JSON string, audio/video only                                                                                              |
| `duration`           | File duration in seconds, audio/video only                                                                                                      |
| `language`           | Recognition language, audio/video only                                                                                                          |
| `deepResearchStatus` | Deep Research status: 0=not started, 1=completed                                                                                                |
| `dprSessionId`       | Deep Research session ID, generated automatically when the file is created and used as the `sessionId` parameter for the Deep Research endpoint |

**`status` processing status enum:**

| code | Name       | Description             |
| ---- | ---------- | ----------------------- |
| -1   | RECORDING  | Recording               |
| 0    | PENDING    | Pending                 |
| 1    | PROCESSING | Processing              |
| 2    | COMPLETED  | Completed               |
| 3    | FAILED     | Failed                  |
| 4    | TRANSSUC   | Transcription succeeded |
| 5    | SUMMARYSUC | Summary succeeded       |

**`transcodeStatus` transcoding status enum:**

| Value       | Description                 |
| ----------- | --------------------------- |
| `null`      | Not started / waiting       |
| `ing`       | Transcoding                 |
| `suc`       | Transcoding succeeded       |
| `fail`      | Transcoding failed          |
| `no_rights` | No permission; VIP required |

**Polling strategy for audio/video transcription:**

After an audio/video file is uploaded, the backend automatically triggers transcoding and transcription. Poll until the completion conditions are met:
1. `transcodeStatus == "suc"` - Transcoding is complete.
2. `status >= 2` - Processing is complete (COMPLETED / TRANSSUC / SUMMARYSUC).
3. `transcribeJson` is not empty - Transcript content has been generated.

Recommended polling parameters:
- Interval: 5 seconds
- Timeout: 10 minutes (600 seconds)
- Exit early when `transcodeStatus == "fail"` or `status == 3` (FAILED)

**File types that require transcoding:** MP3, WAV, MP4, MOV, M4A, CAF, AVI, RMVB, OPUS, AAC; these are the types in `MediaFileTypeEnum` with `uploadNeedTranscode=true`.

Execution:

```bash
# View file details once
python ${SKILL_PATH}/scripts/file_detail.py --token "<TOKEN>" --appkey "<APPKEY>" --record-id "<RECORD_ID>"

# Polling mode: wait for transcription to finish
python ${SKILL_PATH}/scripts/file_detail.py --token "<TOKEN>" --appkey "<APPKEY>" --record-id "<RECORD_ID>" --poll [--interval 5] [--timeout 600]
```

> Output rule: Display only **file name, status, transcoding status, duration, language, and transcript/summary preview**. Do not show internal fields such as `recordId`, `fileId`, `fileType`, or `dprSessionId` to the user.

### 5. Submit Transcription Task

**Endpoint:** `POST /api/v1/task/transcribe/commit`

Manually submit a transcription task after uploading an audio/video file. Use this when automatic transcription is disabled.

**Request body:**

```json
{
  "fileId": 98765,
  "language": "zh",
  "model": "qwen-max-latest",
  "hasSpeakers": true,
  "detailLevel": "more_details",
  "template": "",
  "templateCustomize": ""
}
```

| Field             | Type    | Required | Description                                               |
| ----------------- | ------- | -------- | --------------------------------------------------------- |
| fileId            | long    | Yes      | File ID from upload response `successFiles[].fileId`      |
| language          | string  | No       | Language code, such as `zh` or `en`                       |
| model             | string  | No       | Transcription model                                       |
| hasSpeakers       | boolean | No       | Whether to separate speakers; default false               |
| detailLevel       | string  | No       | Level of detail                                           |
| template          | string  | No       | Template selected by the recorder                         |
| templateCustomize | string  | No       | User-customized template, higher priority than `template` |

**Example response:**

```json
{"code": 0, "data": {"transcribeTaskId": "1876161722453798913"}}
```

Execution:

```bash
python ${SKILL_PATH}/scripts/transcribe_commit.py --token "<TOKEN>" --appkey "<APPKEY>" --file-id <FILE_ID> [--language zh] [--model "qwen-max-latest"] [--has-speakers] [--detail-level "more_details"]
```

### 6. Regenerate Summary for Audio Files

**Endpoint:** `POST /api/v1/task/resummary/commit`

Regenerate a summary from an existing transcription result.

**Request body:**

```json
{
  "fileId": 98765,
  "model": "o4-mini",
  "detailLevel": "more_details",
  "lang": "zh",
  "hasSpeakers": false,
  "template": "",
  "templateCustomize": ""
}
```

| Field             | Type    | Required | Description                                           |
| ----------------- | ------- | -------- | ----------------------------------------------------- |
| fileId            | long    | Yes      | File ID                                               |
| model             | string  | No       | Summary model, such as `qwen-max-latest` or `o4-mini` |
| detailLevel       | string  | No       | Level of detail, such as `more_details`               |
| lang              | string  | No       | Input text language                                   |
| hasSpeakers       | boolean | No       | Whether to separate speakers                          |
| template          | string  | No       | Template                                              |
| templateCustomize | string  | No       | Custom template                                       |

Execution:

```bash
python ${SKILL_PATH}/scripts/resummary_commit.py --token "<TOKEN>" --appkey "<APPKEY>" --file-id <FILE_ID> [--model "o4-mini"] [--detail-level "more_details"] [--lang "zh"] [--has-speakers]
```

### 7. Summarize File for Non-Audio Files

**Endpoint:** `POST /api/project/project/summary/local_file`

Trigger summarization for document files such as PDF or DOC. This can also be used to regenerate a summary.

**Request parameters (query):**

| Parameter   | Type   | Required | Description                                           |
| ----------- | ------ | -------- | ----------------------------------------------------- |
| taskId      | long   | Yes      | File ID, meaning `fileId`                             |
| model       | string | No       | Summary model, such as `qwen-max-latest` or `o4-mini` |
| detailLevel | string | No       | Level of detail, such as `more_details`               |

```bash
curl -X POST "<BASE_URL>/api/project/project/summary/local_file?taskId=<FILE_ID>&model=qwen-max-latest&detailLevel=more_details" \
  -H "Authorization: Bearer <TOKEN>"
```

Execution:

```bash
python ${SKILL_PATH}/scripts/summary_local_file.py --token "<TOKEN>" --appkey "<APPKEY>" --file-id <FILE_ID> [--model "qwen-max-latest"] [--detail-level "more_details"]
```

### 8. Translate

**Endpoint:** `POST /api/v1/translate`

Create a translation task for existing transcript content.

**Request body:**

```json
{
  "transcribeId": 123456,
  "targetLanguage": "en"
}
```

| Field          | Type   | Required | Description                                                                |
| -------------- | ------ | -------- | -------------------------------------------------------------------------- |
| transcribeId   | long   | Yes      | Transcription ID from the `transcribeId` field in the file-detail response |
| targetLanguage | string | Yes      | Target language code, such as `en`, `zh`, or `ja`                          |

**Example response:**

```json
{"code": 0, "data": {"transcribeTaskId": "1876161722453798913"}}
```

Execution:

```bash
python ${SKILL_PATH}/scripts/translate.py --token "<TOKEN>" --appkey "<APPKEY>" --transcribe-id <TRANSCRIBE_ID> --target-language "en"
```

### 9. Share File

#### Create Share

**Endpoint:** `POST /api/share/{shareType}`

| shareType   | Description          |
| ----------- | -------------------- |
| `audio`     | Audio file share     |
| `localFile` | Non-audio file share |

**Request body:** JSON string; contents differ by share type.

**Response:** Returns a share code (`shareCode`).

```json
{"code": 0, "data": "<SHARE_CODE>"}
```

#### Access Share

**Endpoint:** `GET /api/share/{shareType}/{shareCode}`

Use the share code to get shared content.

```bash
curl -X GET "<BASE_URL>/api/share/audio/<SHARE_CODE>"
```

Execution:

```bash
# Create share
python ${SKILL_PATH}/scripts/share.py create --token "<TOKEN>" --appkey "<APPKEY>" --share-type audio --data '<JSON>'

# Access share
python ${SKILL_PATH}/scripts/share.py get --appkey "<APPKEY>" --share-type audio --share-code "<SHARE_CODE>"
```

### 10. Generate Podcast

**Endpoint:** `POST /api/podcast/generate`

Generate podcast audio from a file summary.

**Request body:**

```json
{
  "summaryId": 789012,
  "localFileId": null
}
```

| Field       | Type | Required    | Description                            |
| ----------- | ---- | ----------- | -------------------------------------- |
| summaryId   | long | Conditional | Summary ID, used for audio files       |
| localFileId | long | Conditional | Local file ID, used for document files |

> One of the two is required: pass `summaryId` for audio files, and `localFileId` for document files.

Execution:

```bash
# Audio file
python ${SKILL_PATH}/scripts/podcast_generate.py --token "<TOKEN>" --appkey "<APPKEY>" --summary-id <SUMMARY_ID>

# Document file
python ${SKILL_PATH}/scripts/podcast_generate.py --token "<TOKEN>" --appkey "<APPKEY>" --local-file-id <LOCAL_FILE_ID>
```

### 11. Deep Research

**Endpoint:** `POST /api/v1/deep/research/query`

Start Deep Research based on file content. The key parameter `sessionId` must be obtained from the file-detail endpoint.

**Request body:**

```json
{
  "sessionId": "2032367876959596548",
  "sessionType": 9,
  "question": "Analyze the core arguments of this document",
  "msgId": 1773394072812,
  "outline": "- Core arguments\n- Argument logic",
  "source": 3
}
```

| Field       | Type   | Required | Description                                                                                          |
| ----------- | ------ | -------- | ---------------------------------------------------------------------------------------------------- |
| sessionId   | string | Yes      | Session ID from the `dprSessionId` field returned by `GET /api/v2/file-index/file-detail/{recordId}` |
| sessionType | int    | Yes      | Session type; see enum table below                                                                   |
| question    | string | Yes      | User's research question                                                                             |
| msgId       | long   | No       | Message ID; the backend overwrites it with `System.currentTimeMillis()`, so any value is acceptable  |
| outline     | string | No       | Research outline; can be manually provided or pre-generated by the frontend AI                       |
| source      | int    | No       | Source identifier; the backend does not validate it and uses it only for tracking/statistics         |

**`sessionType` enum (`ChatTypeEnum`):**

| Value | Enum name            | Description                      | `sessionId` source                             |
| ----- | -------------------- | -------------------------------- | ---------------------------------------------- |
| 5     | DEEP_RESEARCH_REPORT | Project-level Deep Research      | `sessionId` under `projectId`                  |
| 6     | FILE_DP_RESEARCH     | **Audio file** Deep Research     | `data.dprSessionId` from audio file details    |
| 9     | LOCAL_FILE_RESEARCH  | **Non-audio file** Deep Research | `data.dprSessionId` from document file details |

> Full `ChatTypeEnum` also includes: 0=ASK_AI_ALL, 1=ASK_AI, 2=CHAT_WITH_SHADOW, 3=AHA_MOMENTS, 4=RANDOM_THOUGHT, 7=FILE_AHA_MOMENTS, 8=WEB_CHAT.

**Steps to obtain `sessionId`:**

```text
1. Call the file-detail endpoint: GET /api/v2/file-index/file-detail/{recordId}
2. Get the value from the response:
   - Audio file -> data.dprSessionId  (sessionType=6)
   - Document file -> data.dprSessionId  (sessionType=9)
3. Use the isVoice field to determine sessionType.
```

**Response:** Returns the research result.

```json
{"code": 0, "data": 123456}
```

Execution:

```bash
# Method 1: pass recordId and automatically obtain dprSessionId and sessionType
python ${SKILL_PATH}/scripts/deep_research.py --token "<TOKEN>" --appkey "<APPKEY>" --record-id <RECORD_ID> --question "Analyze the core arguments of this document"

# Method 2: pass sessionId + sessionType directly
python ${SKILL_PATH}/scripts/deep_research.py --token "<TOKEN>" --appkey "<APPKEY>" --session-id <DPR_SESSION_ID> --session-type 9 --question "Analyze the core arguments of this document"
```

### 12. User Settings (Automatic Transcription)

#### Get Settings

**Endpoint:** `GET /api/v1/user/setting`

```bash
curl -X GET "<BASE_URL>/api/v1/user/setting" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example response:**

```json
{
  "code": 0,
  "data": {
    "autoTranscribeStyle": { "auto": true },
    "languageStyle": { "language": "zh" },
    "transcribeLanguage": { "language": "zh" }
  }
}
```

#### Save Settings

**Endpoint:** `PUT /api/v1/user/setting`

```json
{
  "autoTranscribeStyle": { "auto": true },
  "transcribeLanguage": { "language": "zh" }
}
```

Execution:

```bash
# Get settings
python ${SKILL_PATH}/scripts/user_setting.py get --token "<TOKEN>" --appkey "<APPKEY>"

# Save settings
python ${SKILL_PATH}/scripts/user_setting.py put --token "<TOKEN>" --appkey "<APPKEY>" --data '{"autoTranscribeStyle":{"auto":true}}'
```

### 13. Knowledge-Base File Management

#### Batch Delete

**Endpoint:** `POST /api/v1/knowledge/delete/batch`

**Request body:** Array of `recordId` values.

```json
[2031647298439811075, 2031647298439811076]
```

**Response:** Returns the number of deleted items.

```json
{"code": 0, "data": 2}
```

#### Rename File

**Endpoint:** `PUT /api/v1/knowledge/edit/{recordId}`

**Request body:**

```json
{
  "title": "New file name",
  "color": "#4A90D9",
  "icon": "document"
}
```

| Field | Type   | Required | Description         |
| ----- | ------ | -------- | ------------------- |
| title | string | No       | New title/file name |
| color | string | No       | Color               |
| icon  | string | No       | Icon                |

#### Copy File

**Endpoint:** `POST /api/v1/knowledge/copyTo/{targetParentId}`

Copy a file to the target directory.

**Path parameter:** `targetParentId` - `recordId` of the target directory.

**Request body:** Array of `recordId` values.

```json
[2031647298439811075]
```

**Response:** Returns the copied file list.

```json
{"code": 0, "data": [{"recordId": "...", "title": "..."}]}
```

#### Move File

**Endpoint:** `POST /api/v1/knowledge/moveTo/{targetParentId}`

Move a file to the target directory.

**Path parameter:** `targetParentId` - `recordId` of the target directory.

**Request body:** Array of `recordId` values.

```json
[2031647298439811075]
```

**Response:** Returns the number of moved items.

```json
{"code": 0, "data": 1}
```

Execution:

```bash
# Batch delete
python ${SKILL_PATH}/scripts/knowledge_manage.py delete --token "<TOKEN>" --appkey "<APPKEY>" --record-ids <ID1> <ID2>

# Rename
python ${SKILL_PATH}/scripts/knowledge_manage.py rename --token "<TOKEN>" --appkey "<APPKEY>" --record-id <RECORD_ID> --title "New file name"

# Copy
python ${SKILL_PATH}/scripts/knowledge_manage.py copy --token "<TOKEN>" --appkey "<APPKEY>" --target-parent-id <TARGET_ID> --record-ids <ID1>

# Move
python ${SKILL_PATH}/scripts/knowledge_manage.py move --token "<TOKEN>" --appkey "<APPKEY>" --target-parent-id <TARGET_ID> --record-ids <ID1>
```

## Script Path Notes

`${SKILL_PATH}` = `.codebanana/.skills/ticnote-api`; use `run_terminal_cmd` to run all scripts.

| #   | Function                       | Script                          |
| --- | ------------------------------ | ------------------------------- |
| 2   | Get Token                      | `scripts/get_token.py`          |
| 3   | Knowledge-base project list    | `scripts/list_projects.py`      |
| 4   | File list under project        | `scripts/list_files.py`         |
| 5   | Upload file                    | `scripts/upload_file.py`        |
| 6   | File details / polling         | `scripts/file_detail.py`        |
| 7   | Submit transcription task      | `scripts/transcribe_commit.py`  |
| 8   | Regenerate summary for audio   | `scripts/resummary_commit.py`   |
| 9   | Summarize non-audio file       | `scripts/summary_local_file.py` |
| 10  | Translate                      | `scripts/translate.py`          |
| 11  | Share file                     | `scripts/share.py`              |
| 12  | Generate podcast               | `scripts/podcast_generate.py`   |
| 13  | Deep Research                  | `scripts/deep_research.py`      |
| 14  | User settings                  | `scripts/user_setting.py`       |
| 15  | Knowledge-base file management | `scripts/knowledge_manage.py`   |

## Error Handling

### HTTP-Layer Errors

| HTTP status | Meaning                              | Handling                                |
| ----------- | ------------------------------------ | --------------------------------------- |
| 401         | Token invalid or expired             | Get a new token                         |
| 403         | API Key permissions are insufficient | Ask the user to check key permissions   |
| 413         | File is too large                    | Tell the user about the file size limit |
| 429         | Request rate limit exceeded          | Wait and retry                          |

### Business-Layer Errors (HTTP 200 but `code != 0/200`)

| Business code | Endpoint                   | Meaning                                  | Handling                                                                                                                                                                                                                                                                                                                   |
| ------------- | -------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 503           | `/api/v1/knowledge/upload` | No permission to write to target project | The account linked to the current AppKey is not the owner of that project. **Handling flow:** 1. Tell the user they do not have permission to write to the project. 2. List the projects owned by the current account so the user can choose again. 3. Or ask the user to switch to the AppKey of the corresponding owner. |
| 11865         | `/api/p1/appkey/login`     | Appkey not found                         | See the error code table in section 2                                                                                                                                                                                                                                                                                      |
| 11864         | `/api/p1/appkey/login`     | User not found                           | See the error code table in section 2                                                                                                                                                                                                                                                                                      |
| 11866         | `/api/p1/appkey/login`     | Account not found                        | See the error code table in section 2                                                                                                                                                                                                                                                                                      |

> **Note:** Business-layer 503 is not the same as HTTP 503. The former is a JSON response with `code: 503` returned under HTTP 200, meaning insufficient permissions, such as uploading to a project where the user is not the owner. The latter is true service unavailability. The scripts already detect this and provide a clear message.

## Reference Files

- **API Key guide** (`references/get-apikey.md`) - Detailed steps for obtaining an API Key on the TicNote platform.
