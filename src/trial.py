file_name = "../sample_txt/random1.txt"
with open(file_name,"rb") as f:
    file_content = f.read()
    total_length = len(file_content)
    print(f"Total length of the file: {total_length} bytes")