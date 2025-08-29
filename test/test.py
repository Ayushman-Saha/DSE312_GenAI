from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os

os.environ['GOOGLE_API_KEY'] = 'Not for public repo'

client = genai.Client()

OUTPUT_DIR = "../generated_panels"

number_of_images = 9

def prepare_output_dir():
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                for root, dirs, files in os.walk(file_path, topdown=False):
                    for f in files:
                        os.remove(os.path.join(root, f))
                    for d in dirs:
                        os.rmdir(os.path.join(root, d))
                os.rmdir(file_path)
    else:
        os.makedirs(OUTPUT_DIR)

def story_to_prompts(story_text):
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    You are a professional comic panel designer AI, tasked with converting a short story into a maximum of {number_of_images} illustrated cartoon-style panels, suitable for a children’s storybook.

    Your goal is to break down the story into its most important or funniest moments and generate one panel per moment. Each panel must include:
    
    1. Image Prompt: A detailed, standalone visual description of the scene written for an image generation model Gemini. The style should be vibrant, exaggerated, cartoon-like, and suitable for comic books. Describe characters, setting, actions, facial expressions, and any comedic or whimsical elements. Maintain visual and character consistency across all panels. Make sure to keep the number of characters same across the frames
    
    2. Caption/Dialogue: A short, funny caption or character dialogue line that goes with the panel. Make sure the font is same across
    
    Output format:
    PANEL [Number]
    Image Prompt: [description]
    Caption/Dialogue: "[text]"
    
    Now, generate the panel breakdown for the following story:
    
    {story_text}

    """

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT']
        )
    )

    return response.text.strip().split("PANEL")[1:]


def image_from_prompts(image_prompt):
    model = "gemini-2.0-flash-preview-image-generation"
    prompt = f"""
    {image_prompt}
    
     Generate a comical illustration based on this. The style should be vibrant, exaggerated, cartoon-like, and suitable for comic books. Describe characters, setting, actions, facial expressions, and any comedic or whimsical elements. Maintain visual and character consistency across all panels. Make sure to keep the number of characters same across the frames.Make sure the font is same across
    """

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
        )
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))
    return None


def stitch_the_story(num_images=number_of_images):
    output_file = os.path.join(OUTPUT_DIR, "storybook_stitched.png")

    image_files = sorted([
        os.path.join(OUTPUT_DIR, f)
        for f in os.listdir(OUTPUT_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg')) and 'panel' in f
    ])

    if not image_files:
        raise Exception("No panel images found in the output directory.")

    if num_images is None:
        num_images = len(image_files)

    image_files = image_files[:num_images]
    images = [Image.open(img).convert("RGB") for img in image_files]

    while len(images) < num_images:
        blank = Image.new("RGB", images[0].size, color=(255, 255, 255))
        images.append(blank)

    cols = int(num_images ** 0.5)
    rows = (num_images + cols - 1) // cols  # ceiling division

    img_width, img_height = images[0].size
    stitched_img = Image.new("RGB", (img_width * cols, img_height * rows), color=(255, 255, 255))

    for idx, img in enumerate(images):
        i = idx // cols
        j = idx % cols
        stitched_img.paste(img, (j * img_width, i * img_height))

    stitched_img.save(output_file)
    print(f"Stitched story saved as {output_file}")


def create_comic_book(story_text):
    print("Step 0: Preparing output folder...")
    prepare_output_dir()

    print("Step 1: Analyzing story and generating prompts...")
    prompts = story_to_prompts(story_text)

    generated_images = []

    for i, prompt_segment in enumerate(prompts):
        if not prompt_segment.strip():
            continue

        lines = prompt_segment.strip().split("\n")
        image_prompt = ""
        caption = ""

        for line in lines:
            if line.startswith("Image Prompt:"):
                image_prompt = line.replace("Image Prompt:", "").strip()
            elif line.startswith("Caption/Dialogue:"):
                caption = line.replace("Caption/Dialogue:", "").strip().strip('"')

        print(f"Step 2: Generating image for Panel {i + 1}...")
        final_prompt = f"""
        Create a vibrant, cartoon-style illustration suitable for a children’s storybook.

        Scene: {image_prompt}

        Include the following text within the image as part of the artwork:
        "{caption}"

        Style Guidelines:
        Cartoon-style, colorful, soft-edged, and playful
        Text should be clearly legible, integrated naturally into the scene
        No additional text besides the given caption/dialogue
        Scene and characters should be the primary focus, with expressive poses and exaggerated action
        Storybook aspect ratio should be square 1:1
        """

        image = image_from_prompts(final_prompt)

        if image:
            generated_images.append(image)
            save_path = os.path.join(OUTPUT_DIR, f"panel_{i + 1}.png")
            image.save(save_path)
            print(f"Image for Panel {i + 1} saved as {save_path}")

    print("Step 3: Stitching ...")
    stitch_the_story(len(generated_images))


test_story = """
"""

create_comic_book(test_story)
