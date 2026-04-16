# Error Response Impact Audit

Tai lieu nay tong hop cac thay doi khi chuan hoa error response trong Django + DRF backend.

## 1) Cac endpoint bi anh huong

### 1.1 Anh huong toan cuc (global)

Do da them:
- `REST_FRAMEWORK.EXCEPTION_HANDLER = public_api.exception_handlers.custom_exception_handler`
- `public_api.error_middleware.StandardApiErrorMiddleware`
- `handler404`, `handler403`, `handler500` trong `auth_project.urls`

Nen tat ca endpoint duoi `/api/` deu bi anh huong khi phat sinh cac status sau:
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`
- `405 Method Not Allowed`
- `500 Internal Server Error` (fallback an toan)

### 1.2 Endpoint duoc refactor truc tiep

| Endpoint | Method | Status bi anh huong | Mo ta thay doi |
|---|---|---|---|
| `/api/publications/<publication_id>/` | `GET` | 404, 500 | Doi sang `get_object_or_404`, tranh `DoesNotExist` roi thanh 500 |
| `/api/publications/<publication_id>/` | `PUT` | 404 | Khong tim thay publication tra 404 theo format moi |
| `/api/publications/<publication_id>/` | `DELETE` | 404 | Bo sung `delete()` ro rang, 404 theo format moi |
| `/api/papers/<paper_id>/unmark-downloaded/` | `DELETE` | 404 | Case chua mark truoc do tra 404 theo format moi |
| `/api/datasets/<dataset_id>/unmark-interesting/` | `DELETE` | 404 | Case chua mark truoc do tra 404 theo format moi |
| `/api/dashboard/` | `GET` | 500 | Khong con tra `str(e)`, dung fallback 500 an toan |
| `/api/task-paper-analytics/` | `GET` | 500 | Khong con lo noi dung exception noi bo |
| `/api/tasks/` | `GET` | 500 | Unexpected error tra 500 theo format moi; validation flow giu nguyen DRF |

## 2) Cau truc response moi (bat buoc)

Tat ca loi `401/403/404/405/500` tra ve theo mot JSON duy nhat:

```json
{
  "status": <http_status>,
  "error": "<error_name>",
  "code": "<internal_error_code>",
  "message": "<human_readable_message>",
  "path": "<request_path>",
  "timestamp": "<ISO8601>"
}
```

### Mapping ma loi noi bo

| HTTP Status | error | code | y nghia |
|---|---|---|---|
| 401 | `Unauthorized` | `AUTHENTICATION_REQUIRED` / `AUTHENTICATION_FAILED` | Thieu hoac sai thong tin xac thuc |
| 403 | `Forbidden` | `PERMISSION_DENIED` | Khong du quyen |
| 404 | `Not Found` | `RESOURCE_NOT_FOUND` | Khong tim thay route/tai nguyen |
| 405 | `Method Not Allowed` | `INVALID_HTTP_METHOD` | Dung sai HTTP method |
| 500 | `Internal Server Error` | `INTERNAL_SERVER_ERROR` | Loi khong mong muon (an toan, khong lo stack trace) |

## 3) Vi du response moi

### 401 Unauthorized

```json
{
  "status": 401,
  "error": "Unauthorized",
  "code": "AUTHENTICATION_REQUIRED",
  "message": "Authentication credentials were not provided or are invalid.",
  "path": "/api/profile/",
  "timestamp": "2026-04-07T12:00:00+00:00"
}
```

### 403 Forbidden

```json
{
  "status": 403,
  "error": "Forbidden",
  "code": "PERMISSION_DENIED",
  "message": "You do not have permission to perform this action.",
  "path": "/api/some-endpoint/",
  "timestamp": "2026-04-07T12:00:00+00:00"
}
```

### 404 Not Found

```json
{
  "status": 404,
  "error": "Not Found",
  "code": "RESOURCE_NOT_FOUND",
  "message": "The requested resource was not found.",
  "path": "/api/does-not-exist/",
  "timestamp": "2026-04-07T12:00:00+00:00"
}
```

### 405 Method Not Allowed

```json
{
  "status": 405,
  "error": "Method Not Allowed",
  "code": "INVALID_HTTP_METHOD",
  "message": "This HTTP method is not allowed for this resource.",
  "path": "/api/papers/",
  "timestamp": "2026-04-07T12:00:00+00:00"
}
```

### 500 Internal Server Error

```json
{
  "status": 500,
  "error": "Internal Server Error",
  "code": "INTERNAL_SERVER_ERROR",
  "message": "An unexpected error occurred. Please try again later.",
  "path": "/api/dashboard/",
  "timestamp": "2026-04-07T12:00:00+00:00"
}
```

## 4) Ghi chu quan trong

- Cac response thanh cong (`2xx`) khong bi thay doi.
- Cac loi `400` hien tai trong nhieu endpoint van dang theo format cu (khong nam trong pham vi chuan hoa dot nay).
- Muc tieu dot nay: dam bao `401/403/404/405` (va fallback `500`) luon la JSON theo format thong nhat.
