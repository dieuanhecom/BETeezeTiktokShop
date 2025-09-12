import json
import base64
import httpx
from urllib.parse import quote
import jmespath
from typing import Dict
import requests
def image_to_base64(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
        else:
            print(f"Failed to download image. Status code: {response.status_code}")
            return None
    except Exception as error:
        print(f"An error occurred while converting image to base64: {error}")
        return None

def scrape_user_insta(username):
    try:
        headers = {
            "x-ig-app-id": "936619743392459",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
        }
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        
        response = requests.get(url, headers=headers)
        images_array = []
        if response.status_code == 200:
            data = response.json().get('data', {}).get('user', {})
            if not data:
                print("No user data found.")
                return
            id_user = data["id"]
            with httpx.Client(timeout=httpx.Timeout(20.0)) as session:
                posts = scrape_user_posts(user_id=id_user, session=session, page_size=12, max_pages=10)
                for post in posts:
                    images = []
                    print(post)
                    if post.get("src_attached"):
                        
                        images = [{"id": f"_{post['id']}_{idx}", "url": img_url} for idx, img_url in enumerate(post["src_attached"])]
                    else:
                        images = [{"id": f"_{post['id']}_0", "url": post.get("src", "")}]
                    
                    images_array.append({
                        "id": post.get("id", ""),
                        "siteProductId": "",
                        "url": "",  # This can be omitted or set to None if not needed
                        "domainName": "",
                        "crawler": "",
                        "title": post.get("captions", ""),
                        "description": "",
                        "price": "",
                        "images": images,
                        "optionNames": [],
                        "variants": [],
                        "tags": [],
                    })
                
                return images_array
        else:
            print(f"Failed to get user data. Status code: {response.status_code}")
    except Exception as error:
        print(f"An error occurred: {error}")

def parse_post(data: Dict) -> Dict:
    print(f"parsing post data {data.get('shortcode', 'unknown')}")
    result = jmespath.search("""{
        id: id,
        shortcode: shortcode,
        dimensions: dimensions,
        src: display_url,
        src_attached: edge_sidecar_to_children.edges[].node.display_url,
        has_audio: has_audio,
        video_url: video_url,
        views: video_view_count,
        likes: edge_media_preview_like.count,
        location: location.name,
        taken_at: taken_at_timestamp,
        related: edge_web_media_to_related_media.edges[].node.shortcode,
        type: product_type,
        video_duration: video_duration,
        music: clips_music_attribution_info,
        is_video: is_video,
        tagged_users: edge_media_to_tagged_user.edges[].node.user.username,
        captions: edge_media_to_caption.edges[].node.text,
        comments_count: edge_media_to_parent_comment.count,
        comments_disabled: comments_disabled,
        comments_next_page: edge_media_to_parent_comment.page_info.end_cursor,
        comments: edge_media_to_parent_comment.edges[].node.{
            id: id,
            text: text,
            created_at: created_at,
            owner: owner.username,
            owner_verified: owner.is_verified,
            viewer_has_liked: viewer_has_liked,
            likes: edge_liked_by.count
        }
    }""", data)
    return result

def scrape_user_posts(user_id: str, session: httpx.Client, page_size=20, max_pages: int = None):
    base_url = "https://www.instagram.com/graphql/query/?query_hash=e769aa130647d2354c40ea6a439bfc08&variables="
    variables = {
        "id": user_id,
        "first": page_size,
        "after": None,
    }
    _page_number = 1
    while True:
        resp = session.get(base_url + quote(json.dumps(variables)))
        try:
            data = resp.json()
        except ValueError:
            print(f"Failed to parse JSON response. Content: {resp.content}")
            break

        posts = data.get("data", {}).get("user", {}).get("edge_owner_to_timeline_media", {})
        for post in posts.get("edges", []):
            yield parse_post(post["node"])
        
        page_info = posts.get("page_info", {})
        if not page_info.get("has_next_page"):
            break
        variables["after"] = page_info.get("end_cursor")
        _page_number += 1
        if max_pages and _page_number > max_pages:
            break

# # Example run
# result = scrape_user_insta("vectspace")
# if result:
#     print(json.dumps(result, indent=2))
