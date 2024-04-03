# file_name = "../sample_txt/random1.txt"
# with open(file_name,"rb") as f:
#     file_content = f.read()
#     total_length = len(file_content)
#     print(f"Total length of the file: {total_length} bytes")

a = ["A","B","C","D","E"]

for idx,value in enumerate(a):
    a.remove(value)
    print(f"idx = {idx} corresponding {a[idx]} a is {a}")