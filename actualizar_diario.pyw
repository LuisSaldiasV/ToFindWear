"""Se ejecuta solo al iniciar Windows (sin ventana).

Actualiza el catalogo una vez al dia: si ya se actualizo hoy, no hace nada.
Lo que pasa queda anotado en log.txt.
"""
import io, msvcrt, socket, sys, time, traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).parent
MARCA = BASE / ".ultima_actualizacion"
LOG = BASE / "log.txt"


def hay_internet():
    try:
        socket.create_connection(("www.falabella.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


def main():
    hoy = date.today().isoformat()
    if MARCA.exists() and MARCA.read_text().strip() == hoy and "--forzar" not in sys.argv:
        return
    # evita dos ejecuciones a la vez
    lock = open(BASE / ".actualizando", "w")
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return
    for _ in range(60):          # espera hasta 10 min a que haya red
        if hay_internet():
            break
        time.sleep(10)
    else:
        escribir_log("Sin internet, se intentara en el proximo inicio.\n")
        return
    buf = io.StringIO()
    try:
        sys.path.insert(0, str(BASE))
        import comparador
        with redirect_stdout(buf), redirect_stderr(buf):
            r = comparador.main(["todo"])
        if r == 1:      # config.json con errores: avisar en pantalla y reintentar en el proximo inicio
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, buf.getvalue()[-900:], "Comparador de ropa: revisa config.json", 0x30)
        else:
            MARCA.write_text(hoy)
    except Exception:
        buf.write(traceback.format_exc())
    escribir_log(buf.getvalue())


def escribir_log(texto):
    viejo = LOG.read_text(encoding="utf-8").splitlines()[-1500:] if LOG.exists() else []
    nuevo = f"\n===== {datetime.now():%d-%m-%Y %H:%M} =====\n" + texto
    LOG.write_text("\n".join(viejo) + nuevo, encoding="utf-8")


if __name__ == "__main__":
    main()
