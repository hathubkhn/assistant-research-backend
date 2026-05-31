# Paper → Journal / Conference venue mapping

Workflow để test ~100 papers từ CSV trước khi chạy hàng loạt lên DB.

## Luồng xử lý

1. **DOI** → Crossref + OpenAlex (metadata chính thống).
2. Nếu DOI là **arXiv** (`10.48550/arxiv...`) → lấy title từ metadata → **bỏ qua** bản arXiv khi chọn kết quả cuối.
3. **Title search** → Crossref, OpenAlex, Semantic Scholar (không scrape Google Scholar; Semantic Scholar thường đủ cho CS/ML).
4. **Chọn candidate** có `match_score` cao + có `venue` + ưu tiên bản published (journal/conference) hơn arXiv.
5. **Fuzzy match** tên venue với bảng `journal` / `conference` trong DB.
6. Ghi CSV kèm `status` để review tay trước khi `apply`.

## Conference placeholder "Others"

Tạo bucket tạm cho paper `review` (chạy một lần):

```bash
python manage.py migrate public_api
python manage.py ensure_others_conference
```

- `name`: `Others`
- `rank`: `not rank`
- `abbreviation`, `location`, `url`: để trống

Lấy UUID:

```bash
python manage.py shell -c "from public_api.models import Conference; c=Conference.objects.get(name='Others'); print(c.id)"
```

## Cài dependency

```bash
pip install rapidfuzz pandas openpyxl
```

(`pandas` / `openpyxl` đã dùng cho `import_venues_data`; thêm `rapidfuzz`.)

## Bước 1 — Export 100 papers từ DB

```bash
cd assistant-research-backend
python manage.py map_paper_venues export --limit 100 -o data/venue_mapping_input.csv
```

Tùy chọn hữu ích:

```bash
# Chỉ paper chưa có journal/conference
python manage.py map_paper_venues export --limit 100 --only-missing-venue -o data/venue_mapping_input.csv

# Chỉ arXiv DOI
python manage.py map_paper_venues export --limit 100 --arxiv-only -o data/venue_mapping_input.csv
```

CSV đầu vào:

| paper_id | title | doi | current_journal_id | current_conference_id |
|----------|-------|-----|--------------------|------------------------|

Có thể tự tạo CSV (không cần export) miễn có đủ `paper_id`, `title`, `doi`.

## Bước 2 — Test mapping (gọi API, không ghi DB)

```bash
python manage.py map_paper_venues test \
  -i data/venue_mapping_input.csv \
  -o data/venue_mapping_results.csv \
  --delay 0.5
```

~100 papers × 0.5s delay ≈ vài phút. Kết quả gồm các cột:

| Cột | Ý nghĩa |
|-----|---------|
| `resolved_doi` | DOI publisher (nếu tìm được) |
| `classification` | Journal article / Conference paper / … |
| `venue_from_api` | Tên journal/proceedings từ API |
| `match_score` | Độ khớp title (0–100) |
| `db_venue_kind` | `journal` hoặc `conference` |
| `db_venue_id` | UUID trong DB |
| `db_venue_name` | Tên đã match fuzzy |
| `db_venue_fuzzy_score` | Độ khớp tên venue với DB |
| `status` | `ok_auto` / `review` / `no_venue` / `no_match_db` |

### Review trong Excel

- Lọc `status = ok_auto` → xem nhanh có đúng không.
- `review` → sửa tay cột `db_venue_id`, `db_venue_kind`, `status` thành `ok_auto` nếu OK.
- `no_match_db` → venue chưa có trong DB: chạy `import_venues_data` hoặc tạo `Journal`/`Conference` mới rồi chạy lại `test`.

## Bước 3 — Apply lên DB (dry-run trước)

```bash
python manage.py map_paper_venues apply \
  -i data/venue_mapping_results.csv \
  --dry-run

python manage.py map_paper_venues apply \
  -i data/venue_mapping_results.csv \
  --status ok_auto \
  --update-doi
```

- Mặc định chỉ apply dòng `status=ok_auto`.
- `--update-doi`: cập nhật `paper.doi` sang DOI publisher khi khác arXiv.
- Paper chỉ gán **một** trong hai: `journal` **hoặc** `conference` (xóa FK còn lại).

Apply sau khi đã sửa CSV review:

```bash
python manage.py map_paper_venues apply -i data/venue_mapping_results_reviewed.csv --status ok_auto,review
```

## Model liên quan

```67:83:public_api/models.py
class Paper(models.Model):
    ...
    doi = models.CharField(max_length=200, null=True, blank=True)
    ...
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    conference = models.ForeignKey(Conference, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
```

Logic mapping nằm ở `public_api/services/venue_mapping.py`.

## Lưu ý

- **Rate limit**: tăng `--delay` nếu API trả 429.
- **User-Agent**: sửa email trong `HEADERS` trong `venue_mapping.py`.
- **Google Scholar**: không dùng (ToS / scrape). Semantic Scholar + Crossref + OpenAlex thường đủ; có thể bổ sung sau nếu cần.
- Chạy `import_venues_data` trước để DB có đủ journal/conference → `no_match_db` giảm mạnh.

## Ví dụ arXiv DOI

Input: `10.48550/arXiv.2005.01678`

1. Crossref/OpenAlex trả metadata arXiv + title.
2. Search title → tìm bản CVPR/NeurIPS/… với DOI `10.1109/...` hoặc tương tự.
3. `resolved_doi` + `venue_from_api` → fuzzy match `conference` trong DB.
