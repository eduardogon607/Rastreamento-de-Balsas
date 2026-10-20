import totaltrack
import inspect

# Ver a assinatura da função buscar_dados
print("Assinatura de buscar_dados():")
print(inspect.signature(totaltrack.buscar_dados))
print()

# Ver o código-fonte da função (primeiras 80 linhas)
print("Código-fonte (início):")
src = inspect.getsource(totaltrack.buscar_dados)
for i, linha in enumerate(src.splitlines()[:80], 1):
    print(f"  {i:3} | {linha}")
