import re

input_file = "data/sidecar_log_temp.txt"

def extract_recorded_blocks(input_file):
    p = re.compile("tip (\d{5,6})\.")
    recorded_blocks = []

    with open(input_file) as f:
        f = f.readlines()

    for line in f:
        for pattern in ['Finished']:
            if pattern in line:
                block_number = p.search(line)
                recorded_blocks.append(int(block_number.group(1)))
                break

    return recorded_blocks




def find_missing_blocks(recorded_blocks):
    return [x for x in range(recorded_blocks[0], recorded_blocks[-1]+1) 
                               if x not in recorded_blocks]

recorded_blocks = extract_recorded_blocks(input_file)
missing_blocks = find_missing_blocks(recorded_blocks)
performance = (len(recorded_blocks)-len(missing_blocks))/len(recorded_blocks)

print('## ALL BLOCKS RECORDED ##')
print(recorded_blocks)
print('\n')
print('## BLOCKS MISSED ##')
print(missing_blocks)
print('\n')
print('## PERFORMANCE ##')
print(performance)