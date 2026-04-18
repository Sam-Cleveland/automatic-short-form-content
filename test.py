import difflib

with open('script_in.txt') as f:
    original_text = f.read()
with open('script_out.txt') as f:
    generated_captions = f.read()

# Split the texts into lines
original_lines = original_text.splitlines()
caption_lines = generated_captions.splitlines()

# Create a Differ object
d = difflib.Differ()

# Calculate the differences
diff = d.compare(original_lines, caption_lines)

# Print the results
print('\n'.join(diff))
