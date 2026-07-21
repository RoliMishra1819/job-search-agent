with open('secrets_output.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('private_key'):
            print('Length:', len(line))
            print('Starts with:', repr(line[:50]))
            print('Ends with:', repr(line[-50:]))