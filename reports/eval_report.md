# Hujjat tahlili: aniqlik hisoboti

`python -m scripts.evaluate` tomonidan yaratilgan. To'g'ri javoblar: `data/ground_truth.json`.

## Umumiy natija

| PDF turi   | Hujjat | Rekvizitlar | Topshiriq (recall) | Topshiriq (precision) | Ijrochi | Muddat | Nazorat |
| ---------- | ------ | ----------- | ------------------ | --------------------- | ------- | ------ | ------- |
| Matnli PDF | 6      | 100.0%      | 100.0%             | 100.0%                | 100.0%  | 100.0% | 100.0%  |
| Skaner PDF | 6      | 100.0%      | 97.4%              | 97.4%                 | 100.0%  | 100.0% | 100.0%  |

- **Rekvizitlar**: jo'natuvchi, raqam, sana, imzolagan - to'g'ri topilganlar ulushi.
- **Recall**: hujjatdagi topshiriqlardan nechtasi topildi.
- **Precision**: topilganlardan nechtasi haqiqiy topshiriq.
- **Ijrochi / Muddat**: to'g'ri topilgan topshiriqlar ichida ijrochi / muddat to'g'ri.

## Xatolar

| Hujjat                 | Nima                | Kutilgan                                  | Topildi |
| ---------------------- | ------------------- | ----------------------------------------- | ------- |
| NAMUNA_1_abzats_skaner | topshiriq topilmadi | Ro'yxatga olish departamenti mazkur qaror | -       |
