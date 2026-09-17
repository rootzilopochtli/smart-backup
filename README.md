<div align="center">
  <img src="https://raw.githubusercontent.com/rootzilopochtli/smart-backup/main/banner.jpg" alt="Smart Backup Python" width="100%">
</div>

# Smart Backup 🐧💾

![Status](https://img.shields.io/badge/status-en%20desarrollo-orange)
![License](https://img.shields.io/badge/license-MIT-blue)

**Smart Backup** es una herramienta de línea de comandos (CLI) escrita en Python diseñada para automatizar, organizar y asegurar el proceso de respaldo de un perfil de SysAdmin o Desarrollador en sistemas Linux.

Este proyecto nació de la necesidad de liberar espacio crítico en disco de forma segura, evolucionando de un simple *one-liner* en Bash a un script interactivo.

📖 **Lee la historia completa de su desarrollo, la filosofía de "Las Tres Leyes del SysAdmin" y el uso de la IA como copiloto en mi blog:**
👉 [De Bash a Python: Automatización, IA y las Tres Leyes del SysAdmin](https://www.rootzilopochtli.com/de-bash-a-python-automatizacion-e-ia)

> **⚠️ IMPORTANTE:** No soy un experto en Python; me encuentro en pleno desarrollo de esta habilidad. Este script es el resultado de mi aprendizaje activo, por lo que cualquier sugerencia de mejora, optimización o reporte de errores (vía *Issues* o *Pull Requests*) es más que bienvenida.

---

## ✨ Características Principales

El script ofrece tres modos de operación mediante un menú interactivo:

1. **Modo Personal (Liberación de Espacio):** Analiza tu `$HOME` en busca de los directorios más pesados (por defecto > 5GB). Te permite decidir interactivamente si quieres respaldar una carpeta completa, depurarla internamente o ignorarla. Utiliza `rsync` de forma transaccional para mover los archivos al disco externo y **eliminarlos** del origen solo si la copia fue exitosa.
2. **Modo Sistema (Empaquetado de Entorno):** Toma una "Lista de Oro" de *dotfiles* y directorios esenciales (`.ssh`, `.config`, `.vim`, `.bashrc`, etc.) y los comprime en un archivo `.tar.gz`. Ideal para restaurar tu entorno de trabajo rápidamente tras una reinstalación.
3. **Modo Completo:** Ejecuta ambos respaldos de forma secuencial, organizándolos en un directorio maestro con el *timestamp* del día (ej. `FullBackup_17Sept2026`).

## 🛡️ Seguros y Validaciones Incorporadas

* **Verificación de Espacio (Pre-flight check):** Antes de mover un solo byte, calcula el tamaño de los datos a respaldar y verifica que el disco de destino tenga el espacio suficiente.
* **Detección de FileSystem:** Detecta automáticamente si el disco externo está en un formato de Windows (`exFAT`, `NTFS`, `FAT`) o Linux nativo, ajustando dinámicamente las banderas de `rsync` para evitar errores de permisos al copiar.
* **Logs Limpios:** Mantiene la terminal libre de ruido redirigiendo la salida de `rsync` a un archivo `backup_registro.log` directamente en el disco de respaldo.

---

## 🚀 Requisitos y Uso

### Requisitos
Para ejecutar este script, asegúrate de tener instalados:
* Python 3.x
* `rsync`
* `tar`

### Instalación y Ejecución
Clona este repositorio y ejecuta el script desde tu terminal:

```bash
git clone https://github.com/rootzilopochtli/smart-backup.git
cd smart-backup
python3 smart_backup.py
```

El script te pedirá la ruta de montaje de tu disco externo (ej. `/run/media/usuario/DISCO`) y te guiará paso a paso.

## 🤝 Contribuciones
¿Tienes ideas para hacer el código más "Pythónico", optimizar funciones o agregar nuevas características? ¡Adelante! Siéntete libre de hacer un Fork del repositorio, crear tu rama y enviar un Pull Request.

## 📄 Licencia
Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---
👤 **Alex (@rootzilopochtli)** *Technical Training Developer en Red Hat | Miembro de Fedora Project | Autor de "Fedora Linux System Administration"*
