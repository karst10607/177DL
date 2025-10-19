#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urljoin, urlparse

class ComicDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.177picyy.com/'
        })
        self.base_url = 'https://www.177picyy.com'

    def get_comic_info(self, url):
        """Get comic title and image URLs from a comic page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Get comic title
            title_tag = soup.find('h1', class_='entry-title')
            if not title_tag:
                title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else 'Unknown_Comic'
            
            # Clean up title to make it filesystem-safe
            title = re.sub(r'[\\/*?:"<>|]', '', title).strip()
            
            # Find all image tags
            images = []
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if '177picyy.com' in src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    images.append(src)
            
            # If no images found with src, try data-src or other attributes
            if not images:
                for img in soup.find_all('img'):
                    for attr in ['data-src', 'data-lazy-src']:
                        src = img.get(attr, '')
                        if '177picyy.com' in src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            images.append(src)
                            
            # Get all pages in order
            all_pages = [url]  # Start with the current page
            
            # Find pagination links
            pagination = soup.find('div', class_='pagination')
            if pagination:
                # Extract all page numbers and sort them
                page_links = []
                for a in pagination.find_all('a', href=True):
                    try:
                        # Try to extract page number from URL
                        page_num = int(a['href'].rstrip('/').split('/')[-1])
                        page_links.append((page_num, a['href']))
                    except (ValueError, IndexError):
                        continue
                
                # Sort by page number and add to all_pages
                for num, link in sorted(page_links, key=lambda x: x[0]):
                    if link not in all_pages:  # Avoid duplicates
                        all_pages.append(link)
            
            # Process all pages in order
            for page_url in all_pages:
                try:
                    if page_url != url:  # Skip current page as it's already processed
                        page_response = self.session.get(page_url, timeout=10)
                        page_soup = BeautifulSoup(page_response.text, 'lxml')
                    else:
                        page_soup = soup  # Use already parsed soup for current page
                        
                    # Find images on the page
                    page_images = []
                    for img in page_soup.find_all('img'):
                        src = img.get('src', '')
                        if '177picyy.com' in src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            page_images.append(src)
                    
                    # Maintain order by extending with current page's images
                    images.extend(page_images)
                    
                except Exception as e:
                    print(f"Error processing page {page_url}: {str(e)}")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img in images:
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            
            return {
                'title': title,
                'images': unique_images  # Return ordered, unique images
            }
            
        except Exception as e:
            print(f"Error getting comic info: {str(e)}")
            return None

    def download_images(self, image_urls, output_dir):
        """Download images to the specified directory"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        downloaded = 0
        for i, img_url in enumerate(image_urls, 1):
            try:
                # Get the image filename from the URL
                img_name = os.path.basename(urlparse(img_url).path)
                if not img_name:
                    img_name = f"image_{i:03d}.jpg"
                
                img_path = os.path.join(output_dir, img_name)
                
                # Skip if already downloaded
                if os.path.exists(img_path):
                    print(f"Skipping {img_name} - already exists")
                    continue
                
                print(f"Downloading {img_name}...")
                response = self.session.get(img_url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(img_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                downloaded += 1
                print(f"Downloaded {img_name} successfully!")
                
            except Exception as e:
                print(f"Error downloading {img_url}: {str(e)}")
        
        return downloaded

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 177dl.py <comic_url> [output_directory]")
        print("Example: python3 177dl.py https://www.177picyy.com/html/2025/06/7333200.html/2/ my_comics")
        return
    
    comic_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'downloaded_comics'
    
    downloader = ComicDownloader()
    
    print(f"Fetching comic info from: {comic_url}")
    comic_info = downloader.get_comic_info(comic_url)
    
    if not comic_info or not comic_info['images']:
        print("No comic information or images found!")
        return
    
    print(f"\nComic Title: {comic_info['title']}")
    print(f"Found {len(comic_info['images'])} unique images")
    
    # Create a safe directory name from the comic title
    safe_title = re.sub(r'[\\/*?:"<>|]', '', comic_info['title']).strip()
    comic_dir = os.path.join(output_dir, safe_title)
    
    print(f"\nDownloading to: {os.path.abspath(comic_dir)}")
    
    # Download all images
    downloaded = downloader.download_images(comic_info['images'], comic_dir)
    
    print(f"\nDownload complete! {downloaded} images downloaded to {comic_dir}")

if __name__ == "__main__":
    main()
