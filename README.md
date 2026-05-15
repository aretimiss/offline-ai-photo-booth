# offline-ai-photo-booth

แอปซุ้มถ่ายภาพนักเรียนแบบออฟไลน์ (Kiosk) สำหรับใช้งานด้วยตนเอง โดยเน้นความง่ายและความเป็นส่วนตัว

## คุณสมบัติหลัก (ภาษาไทย)

- หน้าจอเต็ม (Full-screen) สำหรับนักเรียน
- หน้าการใช้งานครบ: ต้อนรับ → เลือกธีม → กล้อง → นับถอยหลัง → ประมวลผล → ผลลัพธ์
- รองรับทั้ง **ท่ามือ** และ **ปุ่มกดขนาดใหญ่**
- ท่ามือที่รองรับ:
  - แบมือ = เริ่ม
  - ชูนิ้วโป้ง = ถ่ายภาพ
  - ปัดซ้าย/ขวา = เปลี่ยนธีม
  - กำมือ = ย้อนกลับ
- โหมดเดโมปลอดภัยเมื่อไม่พบกล้อง
- บันทึกผลลัพธ์ด้วยรหัสสุ่ม (ไม่เก็บชื่อ)
- ลบรูปต้นฉบับของนักเรียนหลังสร้างภาพผลลัพธ์
- อัปโหลดแบบคิวด้วย `rclone`:
  - ออนไลน์ = ซิงก์ทันที
  - ออฟไลน์ = เก็บคิวไว้ก่อน

## ติดตั้ง

1. ใช้ Python 3.11+
2. ติดตั้งแพ็กเกจ:

```bash
pip install -r requirements.txt
```

3. สร้างไฟล์ตั้งค่า:

```bash
cp config/settings.example.json config/settings.json
```

4. ตรวจสอบไฟล์ `data/templates/templates.json` และเพิ่มรูปเทมเพลตจริงตาม path ที่กำหนด

## วิธีรัน

```bash
python -m src.main
```

## หมายเหตุการใช้งานจริง

- ไฟล์ภาพเทมเพลตตัวอย่างใน `templates.json` เป็นชื่อ placeholder ต้องใส่ไฟล์จริงก่อนใช้งานจริง
- โมดูล `src/face_swap.py` เป็น mock engine สำหรับ v1 และสามารถแทนที่ด้วย local AI engine ในภายหลังได้โดยคงเมธอด `swap_face(...)`

---

## Optional English Notes

This is an offline-first student photo booth kiosk app with Thai-first UX. It supports gesture + button controls, mock local face swap, privacy-safe random codes, temporary raw captures, and queued Google Drive sync via `rclone`.
