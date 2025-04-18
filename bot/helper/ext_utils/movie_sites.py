#!/usr/bin/env python3
"""
Movie Websites Domain Utility
----------------------------
This module provides utilities to get the current domains for movie websites and generate RSS feeds.
"""

import random
import time
import asyncio
import re
import urllib.parse
from datetime import datetime
from urllib.parse import urlparse, urljoin, unquote

from httpx import AsyncClient
from bs4 import BeautifulSoup

from bot import LOGGER

# Constants
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]

# Website configurations
MOVIE_WEBSITES = {
    "movierulz": {
        "official_domain": "5movierulz.skin",
        "current_domain": "5movierulz.how",  # Updated domain
        "title_selector": "a[href*='movie-watch-online'], .entry-title a, h2.entry-title a, .post-title a",  # Enhanced selector
        "feed_title": "MovieRulz Latest Movies",
        "feed_description": "Latest movies from MovieRulz",
    },
    "tamilmv": {
        "official_domain": "1tamilmv.com",
        "current_domain": "1tamilmv.cam",
        "title_selector": ".ipsDataItem_title a, .ipsStreamItem_title a, .ipsTruncate a",
        "feed_title": "1TamilMV Latest Movies",
        "feed_description": "Latest movies from 1TamilMV",
    },
    "tamilblasters": {
        "official_domain": "1tamilblasters.net",
        "current_domain": "1tamilblasters.gold",
        "title_selector": ".ipsDataItem_title a, .topic-title a, h3 a, .ipsTruncate a, .ipsContained a, .ipsType_break a",  # Enhanced selector
        "feed_title": "1TamilBlasters Latest Movies",
        "feed_description": "Latest movies from 1TamilBlasters",
    },
}

# Maximum number of items to include in the feed - reduced to prevent memory issues
MAX_ITEMS = 15

# Maximum number of retries for fetching a website
MAX_RETRIES = 3

# Cache for generated RSS feeds
RSS_CACHE = {}

# Cache expiration time in seconds (1 hour)
CACHE_EXPIRATION = 3600


def get_random_user_agent():
    """Return a random user agent from the list."""
    return random.choice(USER_AGENTS)


async def get_current_domain(official_domain, current_domain):
    """
    Try to get the current domain by following redirects from the official domain.
    If that fails, use the provided current domain.
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    # For safety, first check if the current domain is accessible
    try:
        url = f"https://{current_domain}"
        async with AsyncClient(
            headers=headers, follow_redirects=True, timeout=10, verify=False
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                LOGGER.info(f"Current domain {current_domain} is accessible, using it")
                return current_domain
    except Exception as e:
        LOGGER.warning(f"Current domain {current_domain} is not accessible: {e}")

    # Try to find the new domain from the official domain
    try:
        # Try with https first
        url = f"https://www.{official_domain}"
        async with AsyncClient(
            headers=headers, follow_redirects=True, timeout=10, verify=False
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                # Get the final URL after redirects
                final_url = str(response.url)
                domain = urlparse(final_url).netloc
                if domain:
                    LOGGER.info(
                        f"Successfully found current domain: {domain} from {official_domain}"
                    )
                    return domain
    except Exception as e:
        LOGGER.warning(f"Error getting current domain from {official_domain}: {e}")

    try:
        # Try with http if https failed
        url = f"http://www.{official_domain}"
        async with AsyncClient(
            headers=headers, follow_redirects=True, timeout=10, verify=False
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                # Get the final URL after redirects
                final_url = str(response.url)
                domain = urlparse(final_url).netloc
                if domain:
                    LOGGER.info(
                        f"Successfully found current domain: {domain} from {official_domain}"
                    )
                    return domain
    except Exception as e:
        LOGGER.warning(
            f"Error getting current domain from {official_domain} (http): {e}"
        )

    # If all attempts fail, return the current domain
    LOGGER.info(f"Using provided current domain: {current_domain}")
    return current_domain


async def fetch_website_content(url, retries=0):
    """Fetch the content of the website with proper headers and retry logic."""
    if retries >= MAX_RETRIES:
        LOGGER.warning(f"Maximum retries ({MAX_RETRIES}) reached for {url}. Giving up.")
        return None

    # Skip fetching for magnet links - just return the link itself
    if url.startswith("magnet:"):
        LOGGER.debug(f"Skipping HTTP fetch for magnet link: {url}")
        return url

    # Check if URL has a valid protocol
    if not url.startswith("http://") and not url.startswith("https://"):
        LOGGER.warning(f"URL is missing http:// or https:// protocol: {url}")
        # Try to fix the URL by adding https://
        if not url.startswith("//"):
            url = "https://" + url
        else:
            url = "https:" + url
        LOGGER.info(f"Attempting with fixed URL: {url}")

    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    try:
        async with AsyncClient(
            headers=headers, follow_redirects=True, timeout=15, verify=False
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        LOGGER.warning(
            f"Error fetching {url} (attempt {retries + 1}/{MAX_RETRIES}): {e}"
        )
        # Wait before retrying
        await asyncio.sleep(2 * (retries + 1))
        return await fetch_website_content(url, retries + 1)


async def extract_movie_info(html_content, base_url, title_selector):
    """Extract movie information from the HTML content."""
    if not html_content:
        return []

    # Special case for magnet links
    if isinstance(html_content, str) and html_content.startswith("magnet:"):
        LOGGER.info(f"Processing magnet link directly: {html_content[:60]}...")
        magnet_link = html_content

        # Extract title from the magnet link
        title = "Unknown Title"
        dn_match = re.search(r"&dn=([^&]+)", magnet_link)
        if dn_match:
            # Properly decode the URL-encoded title
            encoded_title = dn_match.group(1)
            title = unquote(encoded_title).replace("+", " ")
            # Clean up the title
            title = re.sub(r"www\.[\w\.]+\s*-\s*", "", title)

            # Remove file extensions if present
            title = re.sub(r"\.mkv$|\.mp4$|\.avi$|\.mov$", "", title)

            # Fix any remaining URL encoding issues
            title = title.replace("%20", " ")
            title = title.replace("+", " ")

            # Replace multiple spaces with a single space
            title = re.sub(r"\s+", " ", title)

            LOGGER.info(f"Extracted title from magnet link: {title}")

        # Extract size from the title if possible
        size = 0
        size_regex = re.compile(
            r"(\d+(\.\d+)?\s?(GB|MB|KB|GiB|MiB|KiB|G|M|K))", re.IGNORECASE
        )
        title_match = size_regex.search(title)
        if title_match:
            size_str = title_match.group(1)
            try:
                # Try to parse the size
                size_parts = size_str.lower().strip().split()
                if len(size_parts) == 2:
                    size_value, size_unit = size_parts
                    size_value = float(size_value)
                    if any(unit in size_unit for unit in ["gb", "gib", "g"]):
                        size = int(size_value * 1024 * 1024 * 1024)
                    elif any(unit in size_unit for unit in ["mb", "mib", "m"]):
                        size = int(size_value * 1024 * 1024)
                    elif any(unit in size_unit for unit in ["kb", "kib", "k"]):
                        size = int(size_value * 1024)
            except Exception as e:
                LOGGER.debug(f"Could not parse size from title: {size_str} - {e}")

        # Create a description
        description = f"<h3>{title}</h3>"

        # Add size information if available
        if size > 0:
            try:
                # Format size in a human-readable format
                if size >= 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                elif size >= 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{size / 1024:.2f} KB"
                description += f"<p><strong>Size:</strong> {size_str}</p>"
            except Exception as e:
                LOGGER.debug(f"Error formatting size: {e}")

        # Add magnet link
        description += (
            f"<p><strong>Magnet Link:</strong> <a href='{magnet_link}'>Download</a></p>"
        )

        # Determine site name from the title or base_url
        site_name = "Unknown"
        if "tamilblasters" in title.lower() or "tamilblasters" in base_url.lower():
            site_name = "TamilBlasters"
        elif "tamilmv" in title.lower() or "tamilmv" in base_url.lower():
            site_name = "TamilMV"
        elif "movierulz" in title.lower() or "movierulz" in base_url.lower():
            site_name = "MovieRulz"

        # Add site name
        description += f"<p><strong>Site:</strong> {site_name}</p>"

        # Use current date as publication date
        pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Create a unique guid
        guid = f"{magnet_link.split('&')[0]}"

        # Return the movie info
        return [
            {
                "title": title,
                "link": magnet_link,
                "movie_page_link": base_url,
                "magnet_link": magnet_link,
                "description": description,
                "pub_date": pub_date,
                "guid": guid,
                "size": size,
            }
        ]

    soup = BeautifulSoup(html_content, "html.parser")
    movies = []

    # Special case for TamilBlasters direct movie page
    if (
        "tamilblasters" in base_url.lower()
        and "topic" in base_url
        and any(
            x in base_url.lower()
            for x in ["tamil", "telugu", "hindi", "malayalam", "kannada", "english"]
        )
    ):
        LOGGER.info(
            "Direct movie page detected for TamilBlasters, extracting information"
        )

        # Extract title from the page
        title_element = soup.select_one(".ipsType_pageTitle, .ipsType_break, h1")
        if title_element:
            title = title_element.get_text().strip()

            # Extract magnet link
            magnet_link = ""

            # Method 1: Direct links
            magnet_elements = soup.select('a[href^="magnet:"]')
            if magnet_elements:
                magnet_link = magnet_elements[0]["href"]
                LOGGER.debug("Found direct magnet link for TamilBlasters movie page")

            # Method 2: Look for data attributes
            if not magnet_link:
                data_elements = soup.select(
                    '[data-clipboard-text*="magnet:"], [data-url*="magnet:"]'
                )
                for element in data_elements:
                    for attr in ["data-clipboard-text", "data-url"]:
                        if attr in element.attrs and "magnet:" in element[attr]:
                            magnet_link = element[attr]
                            LOGGER.debug(
                                "Found magnet link in data attribute for TamilBlasters movie page"
                            )
                            break
                    if magnet_link:
                        break

            # Method 3: Look for text containing magnet links
            if not magnet_link:
                for string in soup.stripped_strings:
                    if "magnet:?xt=urn:btih:" in string:
                        magnet_match = re.search(
                            r'(magnet:\?xt=urn:btih:[^"\s]+)', string
                        )
                        if magnet_match:
                            magnet_link = magnet_match.group(1)
                            LOGGER.debug(
                                "Found magnet link in text for TamilBlasters movie page"
                            )
                            break

            # Extract size
            size = 0
            size_regex = re.compile(
                r"(\d+(\.\d+)?\s?(GB|MB|KB|GiB|MiB|KiB|G|M|K))", re.IGNORECASE
            )

            # Look for size in title
            title_match = size_regex.search(title)
            if title_match:
                size_str = title_match.group(1)
                LOGGER.debug(
                    f"Found size information in title: {size_str} for TamilBlasters movie page"
                )
                try:
                    # Try to parse the size
                    size_parts = size_str.lower().strip().split()
                    if len(size_parts) == 2:
                        size_value, size_unit = size_parts
                        size_value = float(size_value)
                        if any(unit in size_unit for unit in ["gb", "gib", "g"]):
                            size = int(size_value * 1024 * 1024 * 1024)
                        elif any(unit in size_unit for unit in ["mb", "mib", "m"]):
                            size = int(size_value * 1024 * 1024)
                        elif any(unit in size_unit for unit in ["kb", "kib", "k"]):
                            size = int(size_value * 1024)
                except Exception as e:
                    LOGGER.debug(f"Could not parse size from title: {size_str} - {e}")

            # Create a description
            description = f"<h3>{title}</h3>"

            # Add size information if available
            if size > 0:
                try:
                    # Format size in a human-readable format
                    if size >= 1024 * 1024 * 1024:
                        size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                    elif size >= 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.2f} MB"
                    else:
                        size_str = f"{size / 1024:.2f} KB"
                    description += f"<p><strong>Size:</strong> {size_str}</p>"
                except Exception as e:
                    LOGGER.debug(f"Error formatting size: {e}")

            # Add magnet link if available
            if magnet_link:
                description += f"<p><strong>Magnet Link:</strong> <a href='{magnet_link}'>Download</a></p>"

            # Add movie page link
            description += (
                f"<p><strong>Source:</strong> <a href='{base_url}'>Visit Page</a></p>"
            )

            # Add site name
            description += "<p><strong>Site:</strong> TamilBlasters</p>"

            # Use current date as publication date
            pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # Use magnet link as the main link if available, otherwise use the movie page link
            link = magnet_link if magnet_link else base_url

            # Add to movies list
            movies.append(
                {
                    "title": title,
                    "link": link,
                    "movie_page_link": base_url,
                    "magnet_link": magnet_link,
                    "description": description,
                    "pub_date": pub_date,
                    "guid": base_url,
                    "size": size,
                }
            )

            # Return early if we found a movie
            if movies:
                return movies

    # Special case for TamilMV and TamilBlasters
    is_tamil_site = "tamilmv" in base_url.lower() or "tamilblasters" in base_url.lower()

    # For TamilMV and TamilBlasters, we need to navigate to movie pages
    if is_tamil_site:
        # Hardcoded movie category URLs for TamilMV and TamilBlasters
        movie_category_urls = []
        if "tamilmv" in base_url.lower():
            movie_category_urls = [
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/13-tamil-new-movies-hdrips-bdrips-dvdrips-hdtv/",
                ),
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/14-tamil-new-movies-tcrip-dvdscr-hdcam-predvd/",
                ),
            ]
        elif "tamilblasters" in base_url.lower():
            movie_category_urls = [
                urljoin(base_url, "/index.php?/forums/forum/6-download-tamil-movies/"),
                urljoin(
                    base_url, "/index.php?/forums/forum/71-download-telugu-movies/"
                ),
            ]

        # Try to fetch a movie category page
        for category_url in movie_category_urls:
            try:
                # Fetch the movie category page
                LOGGER.info(f"Fetching movie category page: {category_url}")
                category_content = await fetch_website_content(category_url)
                if category_content:
                    # Create a new soup for the category page
                    category_soup = BeautifulSoup(category_content, "html.parser")

                    # Look for movie topics in the category page
                    movie_topics = category_soup.select(
                        ".ipsDataItem_title a, .ipsStreamItem_title a, .ipsTruncate a"
                    )
                    if movie_topics:
                        LOGGER.info(
                            f"Found {len(movie_topics)} movie topics in category page"
                        )

                        # Extract movie information from the first few topics
                        for topic in movie_topics[:MAX_ITEMS]:
                            topic_url = urljoin(base_url, topic["href"])
                            topic_title = topic.get_text().strip()

                            # Skip non-movie topics
                            if any(
                                keyword in topic_title.lower()
                                for keyword in [
                                    "forum",
                                    "category",
                                    "index",
                                    "link",
                                    "home",
                                    "page",
                                    "ipl",
                                    "live",
                                    "cricket",
                                ]
                            ):
                                continue

                            # Check if it has movie indicators
                            has_movie_indicators = False
                            movie_indicators = [
                                r"\b(19|20)\d{2}\b",  # Years like 1990, 2023
                                r"\b(720p|1080p|2160p|4k|uhd|hd|fullhd)\b",
                                r"\b(web-?dl|blu-?ray|dvd-?rip|hdrip|hdcam)\b",
                                r"\b(tamil|telugu|hindi|malayalam|kannada|english|dual|multi)\b",
                                r"\b\d+(\.\d+)?\s?(gb|mb|g|m)\b",
                            ]

                            for pattern in movie_indicators:
                                if re.search(pattern, topic_title.lower()):
                                    has_movie_indicators = True
                                    break

                            if not has_movie_indicators:
                                continue

                            # Fetch the movie page to extract magnet links
                            try:
                                # Changed to DEBUG level to reduce log clutter
                                LOGGER.debug(f"Fetching movie page: {topic_url}")
                                movie_page_content = await fetch_website_content(
                                    topic_url
                                )
                                if movie_page_content:
                                    movie_page_soup = BeautifulSoup(
                                        movie_page_content, "html.parser"
                                    )

                                    # Extract magnet link
                                    magnet_link = ""

                                    # Method 1: Direct links
                                    magnet_elements = movie_page_soup.select(
                                        'a[href^="magnet:"]'
                                    )
                                    if magnet_elements:
                                        magnet_link = magnet_elements[0]["href"]
                                        # Changed to DEBUG level to reduce log clutter
                                        LOGGER.debug(
                                            f"Found direct magnet link for {topic_title}"
                                        )

                                    # Method 2: Text containing magnet links
                                    if not magnet_link:
                                        for string in movie_page_soup.stripped_strings:
                                            if "magnet:?xt=urn:btih:" in string:
                                                magnet_match = re.search(
                                                    r'(magnet:\?xt=urn:btih:[^"\s]+)',
                                                    string,
                                                )
                                                if magnet_match:
                                                    magnet_link = magnet_match.group(1)
                                                    LOGGER.info(
                                                        f"Found magnet link in text for {topic_title}"
                                                    )
                                                    break

                                    # Extract size
                                    size = 0
                                    size_regex = re.compile(
                                        r"(\d+(\.\d+)?\s?(GB|MB|KB|GiB|MiB|KiB|G|M|K))",
                                        re.IGNORECASE,
                                    )

                                    # Look for size in title
                                    title_match = size_regex.search(topic_title)
                                    if title_match:
                                        size_str = title_match.group(1)
                                        # Changed to DEBUG level to reduce log clutter
                                        LOGGER.debug(
                                            f"Found size information in title: {size_str} for {topic_title}"
                                        )
                                        try:
                                            # Try to parse the size
                                            size_parts = (
                                                size_str.lower().strip().split()
                                            )
                                            if len(size_parts) == 2:
                                                size_value, size_unit = size_parts
                                                size_value = float(size_value)
                                                if any(
                                                    unit in size_unit
                                                    for unit in ["gb", "gib", "g"]
                                                ):
                                                    size = int(
                                                        size_value * 1024 * 1024 * 1024
                                                    )
                                                elif any(
                                                    unit in size_unit
                                                    for unit in ["mb", "mib", "m"]
                                                ):
                                                    size = int(size_value * 1024 * 1024)
                                                elif any(
                                                    unit in size_unit
                                                    for unit in ["kb", "kib", "k"]
                                                ):
                                                    size = int(size_value * 1024)
                                        except Exception as e:
                                            LOGGER.debug(
                                                f"Could not parse size from title: {size_str} - {e}"
                                            )

                                    # Create a description
                                    description = f"<h3>{topic_title}</h3>"

                                    # Add size information if available
                                    if size > 0:
                                        try:
                                            # Format size in a human-readable format
                                            if size >= 1024 * 1024 * 1024:
                                                size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                                            elif size >= 1024 * 1024:
                                                size_str = (
                                                    f"{size / (1024 * 1024):.2f} MB"
                                                )
                                            else:
                                                size_str = f"{size / 1024:.2f} KB"
                                            description += f"<p><strong>Size:</strong> {size_str}</p>"
                                        except Exception as e:
                                            LOGGER.debug(f"Error formatting size: {e}")

                                    # Add magnet link if available
                                    if magnet_link:
                                        description += f"<p><strong>Magnet Link:</strong> <a href='{magnet_link}'>Download</a></p>"

                                    # Add movie page link
                                    description += f"<p><strong>Source:</strong> <a href='{topic_url}'>Visit Page</a></p>"

                                    # Add site name
                                    site_name = (
                                        "TamilMV"
                                        if "tamilmv" in base_url.lower()
                                        else "TamilBlasters"
                                    )
                                    description += (
                                        f"<p><strong>Site:</strong> {site_name}</p>"
                                    )

                                    # Use current date as publication date
                                    pub_date = datetime.now().strftime(
                                        "%a, %d %b %Y %H:%M:%S +0000"
                                    )

                                    # Use magnet link as the main link if available, otherwise use the movie page link
                                    link = magnet_link if magnet_link else topic_url

                                    # Add to movies list
                                    movies.append(
                                        {
                                            "title": topic_title,
                                            "link": link,
                                            "movie_page_link": topic_url,
                                            "magnet_link": magnet_link,
                                            "description": description,
                                            "pub_date": pub_date,
                                            "guid": topic_url,
                                            "size": size,
                                        }
                                    )

                                    # If we have enough movies, break
                                    if len(movies) >= MAX_ITEMS:
                                        break
                            except Exception as e:
                                LOGGER.error(
                                    f"Error processing movie page {topic_url}: {e}"
                                )

                        # If we found movies, return them
                        if movies:
                            return movies
            except Exception as e:
                LOGGER.error(f"Error fetching movie category page {category_url}: {e}")

    # Try to find movie entries using the provided selector
    movie_entries = soup.select(title_selector)

    if not movie_entries:
        LOGGER.warning(f"No movie entries found using selector: {title_selector}")
        # Try a more general approach
        movie_entries = soup.select(
            'a[href*="movie"], a[href*="topic"], a[href*="download"], a[href*="watch"], h2 a, .entry-title a, .post-title a'
        )

    # Special handling for MovieRulz
    if "movierulz" in base_url.lower() and len(movie_entries) < 5:
        LOGGER.info("Special handling for MovieRulz, trying additional selectors")
        # Try more specific selectors for MovieRulz
        additional_entries = soup.select(
            ".entry-title a, h2.entry-title a, .post-title a, article h2 a"
        )
        if additional_entries:
            LOGGER.info(
                f"Found {len(additional_entries)} additional entries for MovieRulz"
            )
            movie_entries.extend(additional_entries)

    # Modified to include all entries without filtering
    # Only filter out very basic non-content entries
    filtered_entries = []
    for entry in movie_entries:
        title = entry.get_text().strip()
        href = entry.get("href", "")

        # Skip entries with empty titles or hrefs
        if not title or not href:
            continue

        # Skip very short titles (likely not content)
        if len(title) < 3:
            continue

        # Skip entries that are clearly navigation elements
        if title.lower() in ["home", "index", "next", "previous", "page"]:
            continue

        # Include all other entries
        filtered_entries.append(entry)

    # Use filtered entries if we have any, otherwise fall back to original entries
    if filtered_entries:
        LOGGER.info(
            f"Using {len(filtered_entries)} filtered entries instead of all {len(movie_entries)} entries"
        )
        movie_entries = filtered_entries

    if not movie_entries:
        LOGGER.warning("Could not find any movie entries on the page")
        return []

    LOGGER.info(f"Found {len(movie_entries)} potential movie entries")

    for entry in movie_entries[:MAX_ITEMS]:
        # Extract title
        title = entry.get_text().strip()
        if not title:
            # Try to find title in img alt or parent text
            img = entry.find("img")
            if img and "alt" in img.attrs:
                title = img["alt"].strip()
            if not title:
                continue

        # Extract link to the movie page
        movie_page_link = urljoin(base_url, entry["href"])

        # Extract image if available
        img_element = entry.find("img") or entry.parent.find("img")
        image_url = ""
        if img_element and "src" in img_element.attrs:
            image_url = urljoin(base_url, img_element["src"])

        # Initialize magnet link and size as empty
        magnet_link = ""
        size = 0

        # Try to fetch the movie page to extract magnet links and size
        try:
            # Changed to DEBUG level to reduce log clutter
            LOGGER.debug(f"Fetching movie page: {movie_page_link}")
            movie_page_content = await fetch_website_content(movie_page_link)
            if movie_page_content:
                movie_page_soup = BeautifulSoup(movie_page_content, "html.parser")

                # Look for magnet links using multiple methods
                # Method 1: Direct links
                magnet_elements = movie_page_soup.select('a[href^="magnet:"]')
                if magnet_elements:
                    magnet_link = magnet_elements[0]["href"]
                    # Changed to DEBUG level to reduce log clutter
                    LOGGER.debug(f"Found direct magnet link for {title}")

                # Special handling for MovieRulz
                if not magnet_link and "movierulz" in base_url.lower():
                    LOGGER.info("Special handling for MovieRulz magnet links")
                    # Look for download links that might lead to magnet links
                    download_links = movie_page_soup.select(
                        'a[href*="download"], a:-soup-contains("Download"), .entry-content a'
                    )
                    for link in download_links:
                        link_text = link.get_text().strip().lower()
                        if any(
                            text in link_text
                            for text in ["download", "torrent", "magnet"]
                        ):
                            # Try to follow this link to find magnet links
                            download_url = urllib.parse.urljoin(
                                base_url, link.get("href", "")
                            )
                            if download_url and download_url != movie_page_link:
                                try:
                                    LOGGER.info(
                                        f"Following download link: {download_url}"
                                    )
                                    download_page_content = await fetch_website_content(
                                        download_url
                                    )
                                    if download_page_content:
                                        download_page_soup = BeautifulSoup(
                                            download_page_content, "html.parser"
                                        )
                                        # Look for magnet links on the download page
                                        magnet_elements = download_page_soup.select(
                                            'a[href^="magnet:"]'
                                        )
                                        if magnet_elements:
                                            magnet_link = magnet_elements[0]["href"]
                                            LOGGER.info(
                                                f"Found magnet link on download page for {title}"
                                            )
                                            break
                                except Exception as e:
                                    LOGGER.error(
                                        f"Error following download link {download_url}: {e}"
                                    )

                # Method 2: Text containing magnet links
                if not magnet_link:
                    for string in movie_page_soup.stripped_strings:
                        if "magnet:?xt=urn:btih:" in string:
                            magnet_match = re.search(
                                r'(magnet:\?xt=urn:btih:[^"\s]+)', string
                            )
                            if magnet_match:
                                magnet_link = magnet_match.group(1)
                                LOGGER.info(f"Found magnet link in text for {title}")
                                break

                # Method 3: onclick attributes
                if not magnet_link:
                    onclick_elements = movie_page_soup.select('[onclick*="magnet:"]')
                    if onclick_elements:
                        onclick_text = onclick_elements[0]["onclick"]
                        magnet_match = re.search(
                            r'(magnet:\?xt=urn:btih:[^"\s]+)', onclick_text
                        )
                        if magnet_match:
                            magnet_link = magnet_match.group(1)
                            LOGGER.info(f"Found magnet link in onclick for {title}")

                # Method 4: data attributes
                if not magnet_link:
                    data_elements = movie_page_soup.select(
                        '[data-clipboard-text*="magnet:"], [data-url*="magnet:"]'
                    )
                    for element in data_elements:
                        for attr in ["data-clipboard-text", "data-url"]:
                            if attr in element.attrs and "magnet:" in element[attr]:
                                magnet_link = element[attr]
                                LOGGER.info(
                                    f"Found magnet link in data attribute for {title}"
                                )
                                break
                        if magnet_link:
                            break

                # Method 5: Look for torrent hash and construct magnet link
                if not magnet_link:
                    # Look for hash pattern in the page
                    hash_pattern = re.compile(r"[0-9a-fA-F]{40}")
                    for string in movie_page_soup.stripped_strings:
                        hash_match = hash_pattern.search(string)
                        if hash_match and not any(
                            word in string.lower() for word in ["sha1", "sha-1", "hash"]
                        ):
                            torrent_hash = hash_match.group(0)
                            # Construct a basic magnet link
                            magnet_link = f"magnet:?xt=urn:btih:{torrent_hash}&dn={urllib.parse.quote(title)}"
                            LOGGER.info(
                                f"Constructed magnet link from hash for {title}"
                            )
                            break

                # Try to extract file size using multiple methods
                # Method 1: Look for common size patterns like "1.2 GB" or "700 MB"
                size_regex = re.compile(
                    r"(\d+(\.\d+)?\s?(GB|MB|KB|GiB|MiB|KiB|G|M|K))", re.IGNORECASE
                )

                # Method 2: Look for size in title
                title_size_regex = re.compile(
                    r"(\d+(\.\d+)?\s?(GB|MB|KB|GiB|MiB|KiB|G|M|K))", re.IGNORECASE
                )
                title_match = title_size_regex.search(title)
                if title_match:
                    size_str = title_match.group(1)
                    # Changed to DEBUG level to reduce log clutter
                    LOGGER.debug(
                        f"Found size information in title: {size_str} for {title}"
                    )
                    try:
                        # Try to parse the size
                        size_parts = size_str.lower().strip().split()
                        if len(size_parts) == 2:
                            size_value, size_unit = size_parts
                            size_value = float(size_value)
                            if any(unit in size_unit for unit in ["gb", "gib", "g"]):
                                size = int(size_value * 1024 * 1024 * 1024)
                            elif any(unit in size_unit for unit in ["mb", "mib", "m"]):
                                size = int(size_value * 1024 * 1024)
                            elif any(unit in size_unit for unit in ["kb", "kib", "k"]):
                                size = int(size_value * 1024)
                    except Exception as e:
                        LOGGER.debug(
                            f"Could not parse size from title: {size_str} - {e}"
                        )

                # Method 3: Check in the page text if we still don't have a size
                if size == 0:
                    for string in movie_page_soup.stripped_strings:
                        size_match = size_regex.search(string)
                        if size_match:
                            size_str = size_match.group(1)
                            # Changed to DEBUG level to reduce log clutter
                            LOGGER.debug(
                                f"Found size information in page: {size_str} for {title}"
                            )
                            # Convert size to bytes for RSS feed
                            try:
                                from bot.helper.ext_utils.bot_utils import (
                                    get_size_bytes,
                                )

                                size = get_size_bytes(size_str)
                            except Exception as e:
                                LOGGER.debug(f"Using fallback size conversion: {e}")
                                # Fallback if get_size_bytes is not available
                                try:
                                    # Handle different formats (with or without space)
                                    if " " in size_str:
                                        size_parts = size_str.lower().strip().split()
                                        if len(size_parts) == 2:
                                            size_value, size_unit = size_parts
                                            size_value = float(size_value)
                                        else:
                                            continue
                                    else:
                                        # Handle formats like "2.1GB" without space
                                        match = re.match(
                                            r"(\d+(\.\d+)?)(.*)",
                                            size_str.lower().strip(),
                                        )
                                        if match:
                                            size_value = float(match.group(1))
                                            size_unit = match.group(3)
                                        else:
                                            continue

                                    if any(
                                        unit in size_unit for unit in ["gb", "gib", "g"]
                                    ):
                                        size = int(size_value * 1024 * 1024 * 1024)
                                    elif any(
                                        unit in size_unit for unit in ["mb", "mib", "m"]
                                    ):
                                        size = int(size_value * 1024 * 1024)
                                    elif any(
                                        unit in size_unit for unit in ["kb", "kib", "k"]
                                    ):
                                        size = int(size_value * 1024)
                                except Exception as e:
                                    LOGGER.debug(
                                        f"Could not parse size: {size_str} - {e}"
                                    )
                            if size > 0:
                                break

                # Method 4: Try to extract size from magnet link if available
                if size == 0 and magnet_link:
                    # Some magnet links include size information in the name
                    magnet_size_match = size_regex.search(magnet_link)
                    if magnet_size_match:
                        size_str = magnet_size_match.group(1)
                        # Changed to DEBUG level to reduce log clutter
                        LOGGER.debug(
                            f"Found size information in magnet link: {size_str} for {title}"
                        )
                        try:
                            from bot.helper.ext_utils.bot_utils import get_size_bytes

                            size = get_size_bytes(size_str)
                        except Exception as e:
                            LOGGER.debug(
                                f"Could not parse size from magnet link: {size_str} - {e}"
                            )
        except Exception as e:
            LOGGER.error(f"Error fetching movie page {movie_page_link}: {e}")

        # Create a rich description with all available information
        description = f"<h3>{title}</h3>"
        if image_url:
            description += f"<p><img src='{image_url}' alt='{title}' style='max-width:100%;' /></p>"

        # Add size information if available
        if size > 0:
            try:
                # Format size in a human-readable format
                if size >= 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                elif size >= 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{size / 1024:.2f} KB"
                description += f"<p><strong>Size:</strong> {size_str}</p>"
            except Exception as e:
                LOGGER.debug(f"Error formatting size: {e}")

        # Add magnet link if available
        if magnet_link:
            description += f"<p><strong>Magnet Link:</strong> <a href='{magnet_link}'>Download</a></p>"

        # Add movie page link
        description += f"<p><strong>Source:</strong> <a href='{movie_page_link}'>Visit Page</a></p>"

        # Add site name based on the base_url
        site_name = "Unknown"
        if "movierulz" in base_url.lower():
            site_name = "MovieRulz"
        elif "tamilmv" in base_url.lower():
            site_name = "TamilMV"
        elif "tamilblasters" in base_url.lower():
            site_name = "TamilBlasters"
        description += f"<p><strong>Site:</strong> {site_name}</p>"

        # Use current date as publication date since actual dates are not always available
        pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Use magnet link as the main link if available, otherwise use the movie page link
        link = magnet_link if magnet_link else movie_page_link

        movies.append(
            {
                "title": title,
                "link": link,  # This will be the magnet link if available
                "movie_page_link": movie_page_link,  # Always store the movie page link
                "magnet_link": magnet_link,  # Store the magnet link separately
                "description": description,
                "pub_date": pub_date,
                "guid": movie_page_link,  # Use movie page link as guid for consistency
                "size": size,  # Add size information for RSS feed
            }
        )

    return movies


def generate_rss_feed(movies, feed_title, feed_description, feed_link):
    """Generate RSS feed XML from movie information."""
    rss_header = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
    <title>{title}</title>
    <link>{link}</link>
    <description>{description}</description>
    <language>en-us</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    <atom:link href="{link}" rel="self" type="application/rss+xml" />
""".format(
        title=feed_title,
        link=feed_link,
        description=feed_description,
        build_date=datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"),
    )

    # Extract site name from feed title
    site_name = feed_title.split(" ")[0] if feed_title else "Unknown"

    rss_items = ""
    for movie in movies:
        # Enhanced description with magnet link information
        description = movie["description"]

        # Add site name if not already in the description
        if site_name.lower() not in description.lower():
            description += f"<p><strong>Site:</strong> {site_name}</p>"

        if movie.get("magnet_link"):
            description += f"\n\nMagnet Link: {movie['magnet_link']}"

        # Add size information if available
        size_element = ""
        if movie.get("size") and movie["size"] > 0:
            try:
                from bot.helper.ext_utils.status_utils import get_readable_file_size

                size_str = get_readable_file_size(movie["size"])
                description += f"\n\nSize: {size_str}"
                size_element = f"\n        <size>{movie['size']}</size>"
            except Exception as e:
                LOGGER.debug(f"Could not format size: {e}")

        rss_items += """    <item>
        <title>{title}</title>
        <link>{link}</link>
        <description><![CDATA[{description}]]></description>
        <pubDate>{pub_date}</pubDate>
        <guid isPermaLink="true">{guid}</guid>{size}
    </item>
""".format(
            title=movie["title"],
            link=movie["link"],
            description=description,
            pub_date=movie["pub_date"],
            guid=movie["guid"],
            size=size_element,
        )

    rss_footer = """</channel>
</rss>"""

    return rss_header + rss_items + rss_footer


async def get_movie_site_url(site_key):
    """
    Get the current URL for a movie website.
    Returns the URL if successful, None otherwise.
    """
    if site_key not in MOVIE_WEBSITES:
        LOGGER.warning(f"Unknown movie website: {site_key}")
        return None

    site_config = MOVIE_WEBSITES[site_key]

    try:
        # Get the current domain
        domain = await get_current_domain(
            site_config["official_domain"], site_config["current_domain"]
        )

        # Update the current domain in the config
        site_config["current_domain"] = domain

        # Return the URL with https:// protocol
        url = f"https://{domain}"
        LOGGER.debug(f"Generated URL for {site_key}: {url}")
        return url
    except Exception as e:
        LOGGER.error(f"Error getting URL for {site_key}: {e}")
        return None


async def get_tamil_site_rss(site_key):
    """
    Special function to generate RSS feed for TamilMV and TamilBlasters.
    This function navigates directly to movie category pages.
    """
    # Add memory management
    import gc
    import psutil

    # Force garbage collection before starting
    gc.collect()

    # Check memory usage
    memory_info = psutil.virtual_memory()
    if memory_info.percent > 90:  # If memory usage is above 90%
        LOGGER.warning(
            f"High memory usage detected: {memory_info.percent}%. Skipping Tamil site RSS generation."
        )
        return None

    if site_key not in MOVIE_WEBSITES:
        LOGGER.warning(f"Unknown movie website: {site_key}")
        return None

    site_config = MOVIE_WEBSITES[site_key]
    movies = []

    try:
        # Get the current URL
        base_url = await get_movie_site_url(site_key)
        if not base_url:
            LOGGER.error(f"Could not get URL for {site_key}")
            return None

        # Ensure the URL has a protocol
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
            LOGGER.debug(f"Added https:// protocol to URL: {base_url}")

        # Hardcoded movie category URLs for TamilMV and TamilBlasters
        movie_category_urls = []
        if site_key == "tamilmv":
            # Direct URLs to movie pages for TamilMV
            movie_category_urls = [
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/13-tamil-new-movies-hdrips-bdrips-dvdrips-hdtv/",
                ),
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/14-tamil-new-movies-tcrip-dvdscr-hdcam-predvd/",
                ),
                # Add more specific movie category URLs
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/15-tamil-hd-bluray-movies-bdrips-remux-1080p-720p-480p/",
                ),
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/16-tamil-dubbed-movies-bdrips-hdrips-dvdrips-hdtv/",
                ),
                urljoin(
                    base_url,
                    "/index.php?/forums/forum/17-tamil-dubbed-movies-tcrip-dvdscr-hdcam-predvd/",
                ),
            ]
        elif site_key == "tamilblasters":
            # Direct URLs to movie pages for TamilBlasters
            # First try specific movie topic pages that are more likely to have magnet links
            movie_category_urls = [
                # Direct movie pages with known magnet links
                urljoin(
                    base_url,
                    "/index.php?/forums/topic/129670-good-bad-ugly-2025-tamil-1080p-hq-real-predvdrip-x264-aac-45gb-hq-line-audio/",
                ),
                urljoin(
                    base_url,
                    "/index.php?/forums/topic/129765-yamakaathaghi-2025-tamil-1080p-hq-hdrip-x264-ddp-51-192kbps-aac-16gb-esub/",
                ),
                urljoin(
                    base_url,
                    "/index.php?/forums/topic/129918-hostage-2005bdrip-tamil-telugu-hindi-x264-450mb-esubs/",
                ),
                # Tamil HD movies
                urljoin(
                    base_url,
                    "/index.php?/forums/topic/128454-tamil-hd-movies-collection/",
                ),
                # Tamil web series
                urljoin(
                    base_url,
                    "/index.php?/forums/topic/128453-tamil-web-series-collection/",
                ),
                # Tamil dubbed movies
                urljoin(
                    base_url,
                    "/index.php?/forums/topic/128452-tamil-dubbed-movies-collection/",
                ),
                # Then try the category pages
                urljoin(base_url, "/index.php?/forums/forum/6-download-tamil-movies/"),
                urljoin(
                    base_url, "/index.php?/forums/forum/71-download-telugu-movies/"
                ),
                urljoin(
                    base_url, "/index.php?/forums/forum/70-download-malayalam-movies/"
                ),
                urljoin(
                    base_url, "/index.php?/forums/forum/72-download-kannada-movies/"
                ),
                urljoin(base_url, "/index.php?/forums/forum/73-download-hindi-movies/"),
                urljoin(
                    base_url, "/index.php?/forums/forum/74-download-english-movies/"
                ),
            ]

        # Try to fetch a movie category page
        for category_url in movie_category_urls:
            try:
                # Fetch the movie category page
                LOGGER.debug(f"Fetching movie category page: {category_url}")
                category_content = await fetch_website_content(category_url)
                if not category_content:
                    LOGGER.warning(f"Failed to fetch content from {category_url}")
                    continue

                # Create a new soup for the category page
                category_soup = BeautifulSoup(category_content, "html.parser")

                # Look for movie topics in the category page
                movie_topics = category_soup.select(
                    ".ipsDataItem_title a, .ipsStreamItem_title a, .ipsTruncate a, .ipsContained a"
                )

                if not movie_topics:
                    LOGGER.warning(f"No movie topics found in {category_url}")
                    continue

                # Modified to include all topics without filtering
                filtered_topics = []
                for topic in movie_topics:
                    topic_title = topic.get_text().strip()
                    topic_url = topic.get("href", "")

                    # Skip entries with empty titles or hrefs
                    if not topic_title or not topic_url:
                        continue

                    # Skip very short titles (likely not content)
                    if len(topic_title) < 3:
                        continue

                    # Skip entries that are clearly navigation elements
                    if topic_title.lower() in [
                        "home",
                        "index",
                        "next",
                        "previous",
                        "page",
                    ]:
                        continue

                    # Include all other topics
                    filtered_topics.append(topic)

                # Use filtered topics
                if filtered_topics:
                    LOGGER.debug(
                        f"Found {len(filtered_topics)} topics after minimal filtering"
                    )
                    movie_topics = filtered_topics
                else:
                    # Changed to DEBUG level to reduce log clutter
                    LOGGER.debug(
                        f"No topics found after minimal filtering in {category_url}"
                    )
                    continue

                # Extract movie information from the first few topics
                for topic in movie_topics[:MAX_ITEMS]:
                    topic_url = urljoin(base_url, topic["href"])
                    topic_title = topic.get_text().strip()

                    try:
                        # Fetch the movie page to extract magnet links
                        LOGGER.debug(f"Fetching movie page: {topic_url}")
                        movie_page_content = await fetch_website_content(topic_url)
                        if not movie_page_content:
                            LOGGER.warning(f"Failed to fetch content from {topic_url}")
                            continue

                        movie_page_soup = BeautifulSoup(
                            movie_page_content, "html.parser"
                        )

                        # Extract magnet link
                        magnet_link = ""

                        # Special handling for TamilMV
                        if site_key == "tamilmv":
                            # Method 0: Direct links (most reliable for TamilMV based on testing)
                            magnet_elements = movie_page_soup.select(
                                'a[href^="magnet:"]'
                            )
                            if magnet_elements:
                                magnet_link = magnet_elements[0]["href"]
                                LOGGER.debug(
                                    f"Found direct magnet link for {topic_title}"
                                )

                            # Method 1: Look for buttons with magnet links
                            if not magnet_link:
                                buttons = movie_page_soup.select(".ipsButton")
                                for button in buttons:
                                    onclick = button.get("onclick", "")
                                    if "magnet:" in onclick:
                                        magnet_match = re.search(
                                            r'(magnet:\?xt=urn:btih:[^"\s]+)', onclick
                                        )
                                        if magnet_match:
                                            magnet_link = magnet_match.group(1)
                                            LOGGER.debug(
                                                f"Found magnet link in button onclick for {topic_title}"
                                            )
                                            break

                            # Method 2: Look for data attributes with magnet links
                            if not magnet_link:
                                elements_with_data = movie_page_soup.select(
                                    "[data-clipboard-text]"
                                )
                                for element in elements_with_data:
                                    data_text = element.get("data-clipboard-text", "")
                                    if "magnet:" in data_text:
                                        magnet_link = data_text
                                        LOGGER.debug(
                                            f"Found magnet link in data-clipboard-text for {topic_title}"
                                        )
                                        break

                            # Method 3: Look for specific elements with magnet links
                            if not magnet_link:
                                code_blocks = movie_page_soup.select(
                                    "code, pre, .ipsQuote_contents"
                                )
                                for block in code_blocks:
                                    text = block.get_text()
                                    if "magnet:" in text:
                                        magnet_match = re.search(
                                            r'(magnet:\?xt=urn:btih:[^"\s]+)', text
                                        )
                                        if magnet_match:
                                            magnet_link = magnet_match.group(1)
                                            LOGGER.debug(
                                                f"Found magnet link in code block for {topic_title}"
                                            )
                                            break

                        # Special handling for TamilBlasters
                        if not magnet_link and site_key == "tamilblasters":
                            # Method 1: Direct links (most reliable)
                            magnet_elements = movie_page_soup.select(
                                'a[href^="magnet:"]'
                            )
                            if magnet_elements:
                                magnet_link = magnet_elements[0]["href"]
                                LOGGER.debug(
                                    f"Found direct magnet link for TamilBlasters: {topic_title}"
                                )

                            # Method 2: Look for links with specific text patterns
                            if not magnet_link:
                                for link in movie_page_soup.select("a"):
                                    link_text = link.get_text().strip().lower()
                                    if any(
                                        text in link_text
                                        for text in ["magnet", "torrent", "download"]
                                    ):
                                        onclick = link.get("onclick", "")
                                        if "magnet:" in onclick:
                                            magnet_match = re.search(
                                                r'(magnet:\?xt=urn:btih:[^"\s]+)',
                                                onclick,
                                            )
                                            if magnet_match:
                                                magnet_link = magnet_match.group(1)
                                                LOGGER.debug(
                                                    f"Found magnet link in onclick for TamilBlasters: {topic_title}"
                                                )
                                                break

                            # Method 3: Look for data attributes
                            if not magnet_link:
                                data_elements = movie_page_soup.select(
                                    '[data-clipboard-text*="magnet:"], [data-url*="magnet:"]'
                                )
                                for element in data_elements:
                                    for attr in ["data-clipboard-text", "data-url"]:
                                        if (
                                            attr in element.attrs
                                            and "magnet:" in element[attr]
                                        ):
                                            magnet_link = element[attr]
                                            LOGGER.debug(
                                                f"Found magnet link in data attribute for TamilBlasters: {topic_title}"
                                            )
                                            break
                                    if magnet_link:
                                        break

                            # Method 4: Look for specific elements that might contain magnet links
                            if not magnet_link:
                                for div in movie_page_soup.select(
                                    ".ipsQuote_contents, .cPost_contentWrap, .ipsType_richText, .ipsType_normal, .ipsType_break"
                                ):
                                    text = div.get_text()
                                    if "magnet:" in text:
                                        magnet_match = re.search(
                                            r'(magnet:\?xt=urn:btih:[^"\s]+)', text
                                        )
                                        if magnet_match:
                                            magnet_link = magnet_match.group(1)
                                            LOGGER.debug(
                                                f"Found magnet link in div for TamilBlasters: {topic_title}"
                                            )
                                            break

                            # Method 5: Look for hash pattern and construct magnet link
                            if not magnet_link:
                                hash_pattern = re.compile(r"\b([0-9a-fA-F]{40})\b")
                                for string in movie_page_soup.stripped_strings:
                                    if any(
                                        word in string.lower()
                                        for word in ["hash", "torrent", "magnet"]
                                    ):
                                        hash_match = hash_pattern.search(string)
                                        if hash_match and not any(
                                            word in string.lower()
                                            for word in ["sha1", "sha-1"]
                                        ):
                                            torrent_hash = hash_match.group(1)
                                            magnet_link = (
                                                f"magnet:?xt=urn:btih:{torrent_hash}"
                                            )
                                            LOGGER.debug(
                                                f"Found hash and constructed magnet link for TamilBlasters: {topic_title}"
                                            )
                                            break

                        # Method 1: Direct links (for non-TamilMV sites)
                        if not magnet_link and site_key != "tamilmv":
                            magnet_elements = movie_page_soup.select(
                                'a[href^="magnet:"]'
                            )
                            if magnet_elements:
                                magnet_link = magnet_elements[0]["href"]
                                LOGGER.debug(
                                    f"Found direct magnet link for {topic_title}"
                                )

                        # Method 2: Text containing magnet links (for all sites)
                        if not magnet_link:
                            for string in movie_page_soup.stripped_strings:
                                if "magnet:?xt=urn:btih:" in string:
                                    magnet_match = re.search(
                                        r'(magnet:\?xt=urn:btih:[^"\s]+)', string
                                    )
                                    if magnet_match:
                                        magnet_link = magnet_match.group(1)
                                        LOGGER.debug(
                                            f"Found magnet link in text for {topic_title}"
                                        )
                                        break

                        # Method 3: Extract hash and construct magnet link (for all sites)
                        if not magnet_link:
                            # Look for hash patterns
                            hash_pattern = re.compile(r"\b([0-9a-fA-F]{40})\b")
                            for string in movie_page_soup.stripped_strings:
                                hash_match = hash_pattern.search(string)
                                if hash_match:
                                    torrent_hash = hash_match.group(1)
                                    # Construct a basic magnet link
                                    magnet_link = f"magnet:?xt=urn:btih:{torrent_hash}&dn={urllib.parse.quote(topic_title)}"
                                    LOGGER.debug(
                                        f"Constructed magnet link from hash for {topic_title}"
                                    )
                                    break

                        # Extract size
                        size = 0
                        size_regex = re.compile(
                            r"(\d+(\.\d+)?\s?(GB|MB|KB|GiB|MiB|KiB|G|M|K))",
                            re.IGNORECASE,
                        )

                        # Look for size in title
                        title_match = size_regex.search(topic_title)
                        if title_match:
                            size_str = title_match.group(1)
                            LOGGER.debug(
                                f"Found size information in title: {size_str} for {topic_title}"
                            )
                            try:
                                # Try to parse the size
                                size_parts = size_str.lower().strip().split()
                                if len(size_parts) == 2:
                                    size_value, size_unit = size_parts
                                    size_value = float(size_value)
                                    if any(
                                        unit in size_unit for unit in ["gb", "gib", "g"]
                                    ):
                                        size = int(size_value * 1024 * 1024 * 1024)
                                    elif any(
                                        unit in size_unit for unit in ["mb", "mib", "m"]
                                    ):
                                        size = int(size_value * 1024 * 1024)
                                    elif any(
                                        unit in size_unit for unit in ["kb", "kib", "k"]
                                    ):
                                        size = int(size_value * 1024)
                            except Exception as e:
                                LOGGER.debug(
                                    f"Could not parse size from title: {size_str} - {e}"
                                )

                        # Create a description
                        description = f"<h3>{topic_title}</h3>"

                        # Add size information if available
                        if size > 0:
                            try:
                                # Format size in a human-readable format
                                if size >= 1024 * 1024 * 1024:
                                    size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                                elif size >= 1024 * 1024:
                                    size_str = f"{size / (1024 * 1024):.2f} MB"
                                else:
                                    size_str = f"{size / 1024:.2f} KB"
                                description += (
                                    f"<p><strong>Size:</strong> {size_str}</p>"
                                )
                            except Exception as e:
                                LOGGER.debug(f"Error formatting size: {e}")

                        # Add magnet link if available
                        if magnet_link:
                            description += f"<p><strong>Magnet Link:</strong> <a href='{magnet_link}'>Download</a></p>"

                        # Add movie page link
                        description += f"<p><strong>Source:</strong> <a href='{topic_url}'>Visit Page</a></p>"

                        # Use current date as publication date
                        pub_date = datetime.now().strftime(
                            "%a, %d %b %Y %H:%M:%S +0000"
                        )

                        # Use magnet link as the main link if available, otherwise use the movie page link
                        link = magnet_link if magnet_link else topic_url

                        # Add to movies list
                        movies.append(
                            {
                                "title": topic_title,
                                "link": link,
                                "movie_page_link": topic_url,
                                "magnet_link": magnet_link,
                                "description": description,
                                "pub_date": pub_date,
                                "guid": topic_url,
                                "size": size,
                            }
                        )

                        # If we have enough movies, break
                        if len(movies) >= MAX_ITEMS:
                            break
                    except Exception as e:
                        LOGGER.error(f"Error processing movie page {topic_url}: {e}")

                # If we found enough movies, break out of the category loop
                if len(movies) >= MAX_ITEMS:
                    break
            except Exception as e:
                LOGGER.error(f"Error fetching movie category page {category_url}: {e}")

        # If we found movies, generate the RSS feed
        if movies:
            # Generate RSS feed
            LOGGER.debug(
                f"Generating RSS feed for {site_key} with {len(movies)} movies"
            )
            rss_content = generate_rss_feed(
                movies,
                site_config["feed_title"],
                site_config["feed_description"],
                base_url,
            )

            # Cache the RSS feed
            RSS_CACHE[site_key] = {"content": rss_content, "timestamp": time.time()}
            LOGGER.info(
                f"Successfully generated RSS feed for {site_key} with {len(movies)} movies"
            )

            return rss_content
        else:
            LOGGER.warning(f"No movies found for {site_key}")
            return None
    except Exception as e:
        LOGGER.error(f"Error generating RSS feed for {site_key}: {e}")
        return None


async def get_movie_site_rss(site_key, force_refresh=False):
    """
    Generate an RSS feed for a movie website.
    Returns the RSS feed content if successful, None otherwise.
    """
    # Add memory management
    import gc
    import psutil

    # Force garbage collection before starting
    gc.collect()

    # Check memory usage
    memory_info = psutil.virtual_memory()
    if memory_info.percent > 90:  # If memory usage is above 90%
        LOGGER.warning(
            f"High memory usage detected: {memory_info.percent}%. Skipping RSS generation."
        )
        return None

    # Special handling for TamilMV and TamilBlasters
    if site_key in ["tamilmv", "tamilblasters"]:
        LOGGER.debug(
            f"Special handling for {site_key}: navigating directly to movie category pages"
        )
        return await get_tamil_site_rss(site_key)

    # Check if we have a cached version that's still valid
    if (
        site_key in RSS_CACHE
        and time.time() - RSS_CACHE[site_key]["timestamp"] < CACHE_EXPIRATION
    ):
        # Check if the cached feed has proper movie entries
        cached_content = RSS_CACHE[site_key]["content"]
        if "magnet:" in cached_content and any(
            x in cached_content.lower()
            for x in ["1080p", "720p", "bluray", "web-dl", "dvdrip"]
        ):
            # Check if force_refresh is requested
            if force_refresh:
                LOGGER.info(f"Force refreshing RSS feed for {site_key}")
            else:
                LOGGER.debug(f"Using cached RSS feed for {site_key}")
                return cached_content
        else:
            LOGGER.info(
                f"Cached RSS feed for {site_key} doesn't have proper movie entries, regenerating"
            )
            # Clear the cache for this site
            if site_key in RSS_CACHE:
                del RSS_CACHE[site_key]

    if site_key not in MOVIE_WEBSITES:
        LOGGER.warning(f"Unknown movie website: {site_key}")
        return None

    site_config = MOVIE_WEBSITES[site_key]

    try:
        # Get the current URL
        base_url = await get_movie_site_url(site_key)
        if not base_url:
            LOGGER.error(f"Could not get URL for {site_key}")
            return None

        # Ensure the URL has a protocol
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
            LOGGER.debug(f"Added https:// protocol to URL: {base_url}")

        # Fetch the website content
        LOGGER.debug(f"Fetching content from {base_url}")
        html_content = await fetch_website_content(base_url)
        if not html_content:
            LOGGER.error(f"Failed to fetch content from {base_url}")
            return None

        # Extract movie information
        LOGGER.debug(f"Extracting movie information from {base_url}")
        movies = await extract_movie_info(
            html_content, base_url, site_config["title_selector"]
        )

        if not movies:
            LOGGER.warning(f"No movies found on {base_url}")
            return None

        # Generate RSS feed
        LOGGER.debug(f"Generating RSS feed for {site_key} with {len(movies)} movies")
        rss_content = generate_rss_feed(
            movies, site_config["feed_title"], site_config["feed_description"], base_url
        )

        # Cache the RSS feed
        RSS_CACHE[site_key] = {"content": rss_content, "timestamp": time.time()}
        LOGGER.info(
            f"Successfully generated RSS feed for {site_key} with {len(movies)} movies"
        )

        return rss_content
    except Exception as e:
        LOGGER.error(f"Error generating RSS feed for {site_key}: {e}")
        return None
