import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import tempfile

OUTPUT_DIR = "generated_panels"
DEFAULT_NUM_IMAGES = 9


def prepare_output_dir():
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            os.remove(os.path.join(OUTPUT_DIR, filename))
    else:
        os.makedirs(OUTPUT_DIR)


def story_to_prompts(client, story_text, number_of_images=DEFAULT_NUM_IMAGES):
    model = "gemini-2.5-flash-lite"
    prompt = f"""
    You are a professional comic panel designer AI, tasked with converting a short story into a maximum of {number_of_images} illustrated cartoon-style panels, suitable for a children’s storybook.

    Your goal is to break down the story into its most important or funniest moments and generate one panel per moment. Each panel must include:

    1. Image Prompt: A detailed, standalone visual description of the scene.
    2. Caption/Dialogue: A short, funny caption or dialogue line.

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
        config=types.GenerateContentConfig(response_modalities=['TEXT'])
    )

    return response.text.strip().split("PANEL")[1:]


def image_from_prompts(client, image_prompt):
    model = "gemini-2.0-flash-preview-image-generation"

    response = client.models.generate_content(
        model=model,
        contents=image_prompt,
        config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return Image.open(BytesIO(part.inline_data.data))
    return None


def stitch_the_story(images):
    if not images:
        return None

    num_images = len(images)
    cols = int(num_images ** 0.5)
    rows = (num_images + cols - 1) // cols

    img_width, img_height = images[0].size
    stitched_img = Image.new("RGB", (img_width * cols, img_height * rows), color=(255, 255, 255))

    for idx, img in enumerate(images):
        i, j = divmod(idx, cols)
        stitched_img.paste(img, (j * img_width, i * img_height))

    return stitched_img


def main():
    st.set_page_config(page_title="AI Comic Book Generator", layout="wide")
    st.title("AI Comic Book Generator")

    st.markdown("Turn your short story into a colorful comic-style children’s storybook!")

    # Take API key if not provided
    api_key = st.secrets.get("GOOGLE_API_KEY", None)
    if not api_key:
        api_key = st.text_input("Enter your Google API Key", type="password")

    if not api_key:
        st.warning("Please provide your Google API Key to continue.")
        return

    client = genai.Client(api_key=api_key)

    story_text = st.text_area("Enter your story", height=200)

    num_images = st.number_input("Number of panels", min_value=1, max_value=DEFAULT_NUM_IMAGES,
                                 value=DEFAULT_NUM_IMAGES, step=1)

    if st.button("Generate Comic Book", type="primary"):
        if not story_text.strip():
            st.error("Please enter a story first!")
            return

        prepare_output_dir()

        with st.spinner("Analyzing story and generating prompts..."):
            prompts = story_to_prompts(client, story_text, num_images)

        generated_images = []

        for i, prompt_segment in enumerate(prompts):
            lines = prompt_segment.strip().split("\n")
            image_prompt, caption = "", ""

            for line in lines:
                if line.startswith("Image Prompt:"):
                    image_prompt = line.replace("Image Prompt:", "").strip()
                elif line.startswith("Caption/Dialogue:"):
                    caption = line.replace("Caption/Dialogue:", "").strip().strip('"')

            final_prompt = f"""
            Create a vibrant, cartoon-style illustration suitable for a children’s storybook.

            Scene: {image_prompt}

            Include the following text within the image as part of the artwork:
            "{caption}"

            Style Guidelines:
            - Cartoon-style, colorful, playful
            - Text should be clearly legible
            - Square aspect ratio (1:1)
            """

            with st.spinner(f"Generating Panel {i + 1}..."):
                image = image_from_prompts(client, final_prompt)

            if image:
                generated_images.append(image)
                image.save(os.path.join(OUTPUT_DIR, f"panel_{i + 1}.png"))

        if generated_images:
            with st.spinner("Stitching panels into a storybook..."):
                stitched_img = stitch_the_story(generated_images)

            if stitched_img:
                st.image(stitched_img, caption="Final Stitched Storybook", use_container_width=True)

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                stitched_img.save(temp_file.name)

                with open(temp_file.name, "rb") as f:
                    st.download_button(
                        "Download Storybook", f, file_name="storybook.png", mime="image/png"
                    )

                st.success("Done!")


if __name__ == "__main__":
    main()