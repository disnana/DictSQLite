"""GitHubのcode scanningアラートを一括でdismissするスクリプト（適切な理由がない限り非推奨）"""
import asyncio
import aiohttp
import os
from typing import List, Dict

# GitHubトークンを環境変数から取得（またはgh auth tokenで取得）
TOKEN = os.popen("gh auth token").read().strip()
REPO = "disnana/dictsqlite"
API_BASE = "https://api.github.com"


async def fetch_open_alerts(session: aiohttp.ClientSession) -> List[Dict]:
    """openステータスのcode scanningアラート一覧を取得"""
    alerts = []
    page = 1

    while True:
        url = f"{API_BASE}/repos/{REPO}/code-scanning/alerts"
        params = {"state": "open", "per_page": 100, "page": page}
        headers = {
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json"
        }

        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                print(f"Error fetching alerts: {resp.status}")
                break

            data = await resp.json()
            if not data:
                break

            alerts.extend(data)
            print(f"Fetched page {page}: {len(data)} alerts")
            page += 1

            if len(data) < 100:
                break

    return alerts


async def dismiss_alert(
        session: aiohttp.ClientSession,
        alert_number: int,
        semaphore: asyncio.Semaphore
) -> bool:
    """1つのアラートをdismiss"""
    async with semaphore:  # 同時実行数を制限
        url = f"{API_BASE}/repos/{REPO}/code-scanning/alerts/{alert_number}"
        headers = {
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        data = {
            "state": "dismissed",
            "dismissed_reason": "false positive",
            "dismissed_comment": "誤検知のため一括無視"
        }

        async with session.patch(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                print(f"✓ Dismissed alert #{alert_number}")
                return True
            else:
                print(f"✗ Failed alert #{alert_number}: {resp.status}")
                return False


async def main():
    # 同時実行数を50に制限（GitHubのsecondary rate limit対策）
    semaphore = asyncio.Semaphore(50)

    async with aiohttp.ClientSession() as session:
        # Step 1: アラート一覧取得
        print("Fetching open alerts...")
        alerts = await fetch_open_alerts(session)
        print(f"\nTotal open alerts: {len(alerts)}")

        if not alerts:
            print("No open alerts to dismiss.")
            return

        # Step 2: 並列dismiss
        print("\nStarting bulk dismiss...\n")
        tasks = [
            dismiss_alert(session, alert["number"], semaphore)
            for alert in alerts
        ]

        results = await asyncio.gather(*tasks)

        # 結果サマリー
        success = sum(results)
        print(f"\n{'=' * 50}")
        print(f"Dismissed: {success}/{len(alerts)} alerts")
        print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
