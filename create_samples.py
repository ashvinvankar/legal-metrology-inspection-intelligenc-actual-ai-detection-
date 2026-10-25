from PIL import Image, ImageDraw, ImageFont
import os

# Create directory
output_dir = "sample_images"
os.makedirs(output_dir, exist_ok=True)

# Helper function to create an image with text
def create_image(filename, text_lines, color, size=(600, 600)):
    img = Image.new('RGB', size, color=color)
    draw = ImageDraw.Draw(img)
    
    # Use default font since it's guaranteed to be available
    # We scale it up by drawing the text multiple times or just relying on the pipeline's OCR.
    
    y_text = 50
    for line in text_lines:
        # Drawing text at 2x scale manually using default font by drawing it multiple times with offsets
        draw.text((50, y_text), line, fill=(0, 0, 0))
        y_text += 40
        
    img.save(os.path.join(output_dir, filename))

# 1. Front Image
front_text = [
    "AASHIRVAAD",
    "Select Premium Sharbati Atta",
    "100% MP Wheat",
    "Net Weight: 5kg"
]
create_image("1_front_package.jpg", front_text, (255, 235, 205))

# 2. Back Image
back_text = [
    "Nutrition Facts",
    "Energy: 360 kcal",
    "Protein: 11g",
    "Carbohydrates: 76g",
    "Fat: 1.5g",
    "Dietary Fiber: 10g"
]
create_image("2_back_package.jpg", back_text, (240, 248, 255))

# 3. Declaration Label (Crucial for OCR and Rule Engine)
label_text = [
    "MANDATORY DECLARATIONS",
    "----------------------",
    "Product Name: Wheat Flour (Atta)",
    "Net Quantity / Net Weight: 5 kg",
    "MRP: Rs. 299.00 (Incl. of all taxes)",
    "Month & Year of Manufacture: 10/2026",
    "Manufacturer Name: ITC Limited",
    "Address: 37, J.L. Nehru Road, Kolkata 700071",
    "Customer Care Executive:",
    "Phone: 1800-425-44444",
    "Email: quality@itc.in"
]
create_image("3_declaration_label.jpg", label_text, (255, 255, 255), size=(800, 600))

print(f"Successfully generated 3 test images in: {os.path.abspath(output_dir)}")
