import base64
import os
from io import BytesIO

import requests
from PIL import Image
from rembg import remove

background_img_path = "C:/Users/Dell/Downloads/background.jpg"


def remove_background_and_paste(img_url, background_img_path=background_img_path):
    try:
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs("original ", exist_ok=True)
        os.makedirs("masked ", exist_ok=True)

        img_response = requests.get(img_url)
        img = Image.open(BytesIO(img_response.content))

        with BytesIO() as f:
            img.save(f, format="JPEG")
            input_data = f.getvalue()

            subject = remove(
                input_data,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_structure_size=10,
                alpha_matting_base_size=1000,
            )

        with BytesIO(subject) as f:
            foreground_img = Image.open(f)

            with open(background_img_path, "rb") as bg_file:
                background_img = Image.open(bg_file)
                background_img = background_img.resize((img.width, img.height))
                background_img.paste(foreground_img, (0, 0), foreground_img)

                # Save the pasted image to BytesIO
                with BytesIO() as output_buffer:
                    background_img.save(output_buffer, format="JPEG")
                    output_buffer.seek(0)
                    processed_image_data = output_buffer.getvalue()

        # Encode processed image data as base64
        processed_image_base64 = base64.b64encode(processed_image_data).decode("utf-8")

        # Return the base64 encoded image
        return True, processed_image_base64

    except Exception as e:
        return False, str(e)
