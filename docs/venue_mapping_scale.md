# Venue mapping at scale (~896k papers)

## Why 83 days?

Batch 100 chạy ~13 phút vì **mỗi paper gọi API tuần tự** (Crossref + OpenAlex + Semantic Scholar).  
896k × ~8s ≈ **83 ngày** nếu không tối ưu.

## Model mới

| Model | Mục đích |
|-------|----------|
| `VenueLookupCache` | Cache kết quả API theo `doi:...` hoặc `title:...` — paper trùng DOI/title **chỉ gọi API 1 lần** |
| `PaperVenueMapping` | Bảng staging 1-1 với `Paper` — không cần CSV 896k dòng để apply |

`Conference Others` giữ nguyên cho bucket review.

## Ước lượng sau tối ưu

Giả sử **200k unique** lookup keys (DOI/title), ~3 API call/key, ~1.5s/call:

- ~200k × 1.5s ≈ **3.5 ngày** (1 process, `--fast` bỏ Semantic Scholar)
- Nếu **50k unique** → ~**21 giờ**
- Dedupe càng mạnh (nhiều paper trùng DOI) → càng nhanh

## Quy trình khuyến nghị

```bash
# 0) Migrate + Others bucket
python manage.py migrate public_api
python manage.py ensure_others_conference

# 1) Map toàn corpus → DB staging (resume được)
python manage.py map_paper_venues run \
  --only-missing-venue \
  --fast \
  --resume \
  --write-batch 2000 \
  --log-every 1000

# 2) Apply ok_auto + update DOI (bulk, nhanh)
python manage.py map_paper_venues apply-db \
  --status ok_auto \
  --update-doi \
  --dry-run

python manage.py map_paper_venues apply-db \
  --status ok_auto \
  --update-doi

# 3) Gán review → Others rồi apply
python manage.py map_paper_venues apply-db \
  --status review \
  --assign-others \
  --dry-run

python manage.py map_paper_venues apply-db \
  --status review \
  --assign-others

# 4) Import venue từ no_match_db → chỉ re-run subset
python manage.py map_paper_venues run \
  --only-missing-venue \
  --fast \
  --resume
```

## Xem kết quả qua CSV

**Cách 1 — Mẫu nhỏ (gọi API trực tiếp, ra CSV ngay):**

```bash
python manage.py map_paper_venues export --limit 100 -o data/venue_mapping_input.csv
python manage.py map_paper_venues test -i data/venue_mapping_input.csv -o data/venue_mapping_results.csv
```

**Cách 2 — Sau lệnh `run` (đọc từ DB staging):**

```bash
python manage.py map_paper_venues export-results -o data/venue_mapping_from_db.csv
python manage.py map_paper_venues export-results -o data/venue_mapping_no_match_db.csv --status no_match_db
```

## Cờ quan trọng

| Cờ | Ý nghĩa |
|-----|---------|
| `--only-missing-venue` | Bỏ qua paper đã có journal/conference |
| `--fast` | Bỏ Semantic Scholar |
| `--resume` | Bỏ paper đã có `PaperVenueMapping` |
| `--write-batch` | Bulk upsert staging mỗi N paper |
| `apply-db --assign-others` | Review → Conference Others trước khi gán FK |

## Song song (tùy chọn sau)

Chạy nhiều process **chia shard** theo `paper.id` (vd hash % 4) trên DB copy hoặc cùng DB với `--resume` — cần rate limit chung để tránh 429 Crossref.
