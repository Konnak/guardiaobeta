#!/usr/bin/env python3
"""Script para verificar problemas de sintaxe em moderacao.py"""

import ast
import traceback

def check_syntax():
    try:
        with open('cogs/moderacao.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tenta compilar o código
        ast.parse(content)
        print("✅ Sintaxe válida!")
        
    except SyntaxError as e:
        print(f"❌ Erro de sintaxe:")
        print(f"   Linha {e.lineno}: {e.msg}")
        print(f"   Texto: {e.text.strip() if e.text else 'N/A'}")
        
        # Mostra o contexto ao redor da linha problemática
        lines = content.split('\n')
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 5)
        
        print(f"\n📋 Contexto (linhas {start+1}-{end}):")
        for i in range(start, end):
            marker = ">>> " if i == e.lineno - 1 else "    "
            print(f"{marker}{i+1:4}: {lines[i]}")
            
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_syntax()
