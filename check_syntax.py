#!/usr/bin/env python3
import ast
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Tenta compilar o código
        ast.parse(source, filename=filename)
        print(f"✅ {filename} - Sintaxe válida!")
        return True
        
    except SyntaxError as e:
        print(f"❌ {filename} - Erro de sintaxe:")
        print(f"   Linha {e.lineno}: {e.text.strip() if e.text else ''}")
        print(f"   Erro: {e.msg}")
        return False
        
    except IndentationError as e:
        print(f"❌ {filename} - Erro de indentação:")
        print(f"   Linha {e.lineno}: {e.text.strip() if e.text else ''}")
        print(f"   Erro: {e.msg}")
        return False
        
    except Exception as e:
        print(f"❌ {filename} - Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    filename = "cogs/moderacao.py"
    if check_syntax(filename):
        sys.exit(0)
    else:
        sys.exit(1)
