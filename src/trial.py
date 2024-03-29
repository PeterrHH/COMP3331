A = [1, 2, 3, 4]
B = [9, 3, 4, 5]

for a in A:
    if a in B:
        B.remove(a)
        break  # Exit the loop after removing the first matching element

print(B)  # Output: [3, 4, 5]
