# sakana

e5489 Playwright Automation and LINE Notification Integration

## 構成ツール一覧

1. **ginga_kinan.py**
   - WEST EXPRESS 銀河（紀南コース：京都⇔新宮）の空席情報を Playwright を用いてスクレイピングし、空席がある場合のみ LINE Messaging API で通知します。
   - 重複通知を抑制するため、`last_state.json` にて空席状態を追跡し、連続する同一空席の通知を最大3回までスキップします。

2. **ginga_sanin.py**
   - WEST EXPRESS 銀河（山陰コース：京都⇔出雲市）の空席情報を Playwright で取得し、空席発生時に LINE で通知します。

3. **sunrise.py**
   - サンライズ瀬戸・出雲の当日の空席情報および、東京・高松・出雲の天気情報を取得し、LINE でプッシュ通知します（空き状況に関わらず毎日通知）。

## GitHub Actions 実行設定

- `ginga-checker.yml` により、`ginga_kinan.py` が JST 6:00 から 22:00 まで 2時間おきに自動実行されます。
- 空席履歴の状態ファイル `last_state.json` およびダッシュボード履歴ファイル `docs/history.json` は、ワークフロー終了時に自動コミット＆プッシュされます。