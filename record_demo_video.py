import os
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_DIR = Path("/config/.gemini/antigravity/brain/3cf2cf4b-e293-4d50-9c97-cf49eb89f426")
VIDEO_DIR = ARTIFACT_DIR / "demo_video"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

async def record_demo():
    print("Starting Playwright demo recording...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1280, "height": 800}
        )

        page = await context.new_page()
        
        print("Navigating to live Cloud Run app...")
        await page.goto("https://recipe-assistant-frontend-17832453200.us-east1.run.app", wait_until="networkidle")
        await asyncio.sleep(2)

        # Step 1: Allergy Record Prompt (What app does best)
        prompt_1 = "I am allergic to prawn, peanuts, and dairy. Please record my allergies."
        print(f"Executing Prompt 1: '{prompt_1}'")
        
        chat_input = page.locator("#chat-input")
        send_btn = page.locator("#send-btn")

        await chat_input.fill(prompt_1)
        await asyncio.sleep(1)
        await send_btn.click()

        print("Waiting for Agent response for Prompt 1...")
        # Wait for second agent message (welcome is 1st)
        await page.wait_for_function("document.querySelectorAll('.dialogue-row.agent').length >= 2", timeout=60000)
        await asyncio.sleep(4)

        # Open Sidebar Drawer to show feature 5
        print("Opening Sidebar Navigation Drawer...")
        menu_btn = page.locator(".menu-toggle-btn")
        close_btn = page.locator(".close-drawer-btn")
        
        await menu_btn.click()
        await asyncio.sleep(3)
        await close_btn.click() # Close drawer properly using close button
        await asyncio.sleep(1)

        # Step 2: Richer Prompt with Tool Call, DB Lookup & Recipe Card
        prompt_2 = "Now suggest a delicious Mediterranean pasta recipe for 4 people excluding my allergies, and generate a photo of the dish!"
        print(f"Executing Prompt 2: '{prompt_2}'")

        await chat_input.fill(prompt_2)
        await asyncio.sleep(1)
        await send_btn.click()

        print("Waiting for Agent response for Prompt 2...")
        await page.wait_for_function("document.querySelectorAll('.dialogue-row.agent').length >= 3", timeout=90000)
        await asyncio.sleep(8) # Allow full rendering of card and images

        print("Finished recording scenario. Closing context...")
        await page.close()
        await context.close()
        await browser.close()

    # Locate generated webm file
    video_files = list(VIDEO_DIR.glob("*.webm"))
    if video_files:
        src_video = video_files[0]
        dest_webm = ARTIFACT_DIR / "agent_demo.webm"
        dest_mp4 = ARTIFACT_DIR / "agent_demo.mp4"
        
        os.system(f"cp '{src_video}' '{dest_webm}'")
        print(f"Demo video saved to WebM: {dest_webm}")

        # Convert to MP4 using ffmpeg for wide browser compatibility
        cmd_ffmpeg = f"ffmpeg -y -i '{dest_webm}' -c:v libx264 -preset fast -pix_fmt yuv420p '{dest_mp4}'"
        os.system(cmd_ffmpeg)
        print(f"Converted demo video to MP4: {dest_mp4}")
    else:
        print("No video file was captured.")

if __name__ == "__main__":
    asyncio.run(record_demo())
