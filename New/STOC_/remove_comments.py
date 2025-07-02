import re

def remove_comments_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove comentários que começam com # (mas preserva strings que contêm #)
        # Remove apenas comentários que não estão dentro de strings
        if line.strip().startswith('#'):
            # Linha que é só comentário - remove completamente
            continue
        else:
            # Remove comentários inline (depois do código)
            # Mas cuidado com strings que contêm #
            in_string = False
            quote_char = None
            comment_start = -1
            
            for i, char in enumerate(line):
                if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        quote_char = char
                    elif char == quote_char:
                        in_string = False
                        quote_char = None
                elif char == '#' and not in_string:
                    comment_start = i
                    break
            
            if comment_start != -1:
                # Remove o comentário inline
                line = line[:comment_start].rstrip()
            
            cleaned_lines.append(line)
    
    # Remove linhas vazias excessivas (mais de 2 consecutivas)
    final_lines = []
    empty_count = 0
    
    for line in cleaned_lines:
        if line.strip() == '':
            empty_count += 1
            if empty_count <= 2:
                final_lines.append(line)
        else:
            empty_count = 0
            final_lines.append(line)
    
    cleaned_content = '\n'.join(final_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"Comentários removidos de {file_path}")

if __name__ == "__main__":
    remove_comments_from_file(r"c:\Users\corde\Documents\New\STOC_\main.py")
