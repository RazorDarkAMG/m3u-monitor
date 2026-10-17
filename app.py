import json
import os
import time
import uuid
import threading
import fcntl
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import requests
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify, send_file, Response

app = Flask(__name__)

APP_VERSION = "0.4"
DEV_NAME = "Gemini"
GITHUB_URL = "https://github.com/RazorDarkAMG/m3u-monitor"

DATA_DIR = "/data"
ACCOUNTS_PATH = os.path.join(DATA_DIR, "accounts.json")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
NOTIFS_PATH = os.path.join(DATA_DIR, "notifications.json")
KEY_PATH = os.path.join(DATA_DIR, "secret.key")
SCHED_LOCK_PATH = os.path.join(DATA_DIR, "scheduler.lock")

file_lock = threading.Lock()

FAVICON_SVG = """<svg width="512" height="512" viewBox="0 0 120 110" fill="none" xmlns="http://www.w3.org/2000/svg">
    <line x1="42" y1="22" x2="28" y2="6" stroke="#b45309" stroke-width="4" stroke-linecap="round"/>
    <circle cx="26" cy="5" r="4.5" fill="#b45309"/>
    <line x1="62" y1="22" x2="78" y2="6" stroke="#b45309" stroke-width="4" stroke-linecap="round"/>
    <circle cx="80" cy="5" r="4.5" fill="#b45309"/>
    <rect x="12" y="22" width="82" height="62" rx="14" fill="#271705" stroke="#b45309" stroke-width="5"/>
    <rect x="20" y="30" width="54" height="46" rx="8" fill="#180e02" stroke="#78350f" stroke-width="2"/>
    <polygon points="40,42 40,64 60,53" fill="#f97316"/>
    <circle cx="83" cy="39" r="3.5" fill="#f97316"/>
    <circle cx="83" cy="50" r="3.5" fill="#f97316"/>
    <line x1="28" y1="84" x2="22" y2="96" stroke="#b45309" stroke-width="5" stroke-linecap="round"/>
    <line x1="74" y1="84" x2="80" y2="96" stroke="#b45309" stroke-width="5" stroke-linecap="round"/>
    <rect x="65" y="52" width="38" height="38" rx="8" fill="#fef3c7" stroke="#f97316" stroke-width="3"/>
    <path d="M65 62 C65 56, 103 56, 103 62" fill="#f97316"/>
    <line x1="74" y1="49" x2="74" y2="56" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>
    <line x1="94" y1="49" x2="94" y2="56" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>
    <line x1="72" y1="69" x2="88" y2="69" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
    <line x1="72" y1="76" x2="85" y2="76" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
    <line x1="72" y1="83" x2="82" y2="83" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
    <circle cx="98" cy="84" r="14" fill="#f97316" stroke="#fef3c7" stroke-width="2.5"/>
    <polyline points="98,76 98,84 104,88" stroke="#fef3c7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

def init_crypto():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    else:
        with open(KEY_PATH, "rb") as f:
            key = f.read().strip()
    return key

MASTER_KEY = init_crypto()
app.secret_key = MASTER_KEY
fernet = Fernet(MASTER_KEY)

def encrypt_str(val):
    if not val:
        return ""
    if val.startswith("enc:"):
        return val
    token = fernet.encrypt(val.encode("utf-8")).decode("utf-8")
    return f"enc:{token}"

def decrypt_str(val):
    if not val:
        return ""
    if val.startswith("enc:"):
        try:
            token = val[4:].encode("utf-8")
            return fernet.decrypt(token).decode("utf-8")
        except Exception:
            return ""
    return val

TRANSLATIONS = {
    "fr": {
        "subtitle": "Suivi des identifiants et dates d'expiration Xtream Codes",
        "add_playlist": "Ajouter une playlist",
        "refresh_all": "Tout actualiser",
        "settings_btn": "Paramètres",
        "logout": "Déconnexion",
        "no_playlist": "Aucune playlist enregistrée dans votre espace.",
        "no_playlist_sub": "Cliquez sur le bouton ci-dessous pour ajouter votre première liste via un lien M3U ou ses identifiants Xtream.",
        "add_first": "Ajouter ma première playlist",
        "sync_card": "Synchroniser cette playlist",
        "edit": "Modifier",
        "delete": "Supprimer",
        "confirm_delete": "Supprimer la playlist",
        "server": "Serveur",
        "username": "Identifiant",
        "password_hover": "Mot de passe (Survoler)",
        "copy_btn": "Copier",
        "copied": "✓ Copié !",
        "expiration": "Expiration :",
        "time_left": "Temps restant :",
        "active_cons": "Connexions actives :",
        "last_sync": "Dernière MàJ :",
        "never": "Jamais",
        "copy_m3u": "Copier URL M3U complète",
        "modal_add_title": "Ajouter une playlist",
        "modal_edit_title": "Modifier la playlist",
        "playlist_name": "Nom de la playlist / Proche *",
        "playlist_name_ph": "Ex: Salon, Parents, Frère...",
        "quick_fill": "⚡ Remplissage auto par lien M3U (Optionnel)",
        "quick_fill_ph": "Collez le lien http://.../get.php?username=... ici",
        "quick_fill_help": "Extrait automatiquement le serveur, l'identifiant et le mot de passe.",
        "server_label": "Serveur *",
        "username_label": "Identifiant *",
        "password_label": "Mot de passe *",
        "gotify_toggle": "🔔 Activer les notifications Gotify pour cette playlist",
        "gotify_url": "URL du serveur Gotify (ex: http://192.168.1.3:8080)",
        "gotify_token": "Token de l'application Gotify",
        "gotify_days": "Alerter à partir de X jours restants",
        "gotify_freq": "Répéter l'alerte tous les X jours",
        "gotify_custom_msg": "Message personnalisé (Optionnel - Variables : {nom}, {days}, {date})",
        "gotify_custom_ph": "Laisser vide pour utiliser le message traduit par défaut",
        "gotify_test_btn": "📡 Tester la notification Gotify",
        "gotify_testing": "Envoi en cours...",
        "gotify_test_ok": "✓ Notification reçue sur Gotify !",
        "gotify_test_err": "❌ Échec : vérifiez l'URL et le Token",
        "gotify_alert_title": "⚠️ Expiration IPTV : {nom}",
        "gotify_alert_body": "La playlist '{nom}' expire dans {days} jours (le {date}).",
        "gotify_test_title": "🔔 Test M3U-Monitor : {nom}",
        "gotify_test_body": "Connexion Gotify réussie pour la playlist '{nom}' !",
        "cancel": "Annuler",
        "save": "Enregistrer",
        "status_active": "Actif",
        "status_expired": "Expiré",
        "status_invalid": "Identifiants invalides",
        "status_unreachable": "Serveur injoignable",
        "status_unknown": "Inconnu",
        "status_http_err": "Erreur HTTP",
        "unlimited": "Illimité",
        "days": "jours",
        "expired_days": "Expiré ({days} j)",
        "at_time": "à",
        "setup_title": "Initialisation de M3U-Monitor",
        "setup_sub": "Créez le premier compte Administrateur pour sécuriser l'application.",
        "login_title": "Connexion",
        "login_sub": "Accédez à vos playlists IPTV personnelles",
        "register_title": "Créer un compte",
        "register_sub": "Créez votre espace personnel pour gérer vos playlists",
        "user_field": "Nom d'utilisateur",
        "pass_field": "Mot de passe",
        "login_btn": "Se connecter",
        "register_btn": "S'inscrire",
        "setup_btn": "Créer le compte Administrateur",
        "no_account_yet": "Pas encore de compte ?",
        "create_account_link": "Créer un compte",
        "already_account": "Déjà un compte ?",
        "login_link": "Se connecter",
        "err_invalid_login": "Identifiant ou mot de passe incorrect.",
        "err_user_exists": "Ce nom d'utilisateur existe déjà.",
        "err_reg_disabled": "L'inscription publique est désactivée par l'administrateur.",
        "settings_title": "Paramètres",
        "tab_general": "Langue",
        "tab_scheduler": "Mise à jour auto",
        "tab_users": "Utilisateurs",
        "tab_about": "À propos",
        "choose_lang": "Langue de l'interface",
        "sched_enable": "Activer la vérification automatique en arrière-plan",
        "sched_every_days": "Vérifier les playlists tous les (jours) :",
        "sched_at_time": "Heure d'exécution (HH:MM) :",
        "sched_last_run": "Dernière exécution automatique :",
        "sched_run_now": "⚡ Tester le planificateur maintenant",
        "sched_save": "Enregistrer la planification",
        "allow_reg_label": "Autoriser la création de compte sur la page de connexion",
        "add_user_section": "Créer un nouvel utilisateur",
        "role_admin": "Admin",
        "role_user": "Utilisateur",
        "create_user_btn": "Ajouter",
        "confirm_del_user": "Supprimer cet utilisateur et toutes ses playlists ?",
        "about_desc": "Gestionnaire léger d'identifiants et d'expirations Xtream Codes / M3U.",
        "about_version": "Version installée",
        "about_dev": "Développé avec",
        "about_github": "Code source GitHub",
        "notif_center": "Notifications",
        "notif_clear": "Tout effacer",
        "notif_empty": "Aucune notification pour le moment.",
        "toast_sync_start": "Actualisation de la playlist « {nom} » en cours...",
        "toast_sync_done": "Playlist « {nom} » mise à jour avec succès ({status} - Connexions : {cons}).",
        "toast_sync_err": "Erreur lors de l'actualisation de « {nom} ».",
        "toast_sync_all_start": "Actualisation de toutes les playlists en cours...",
        "toast_sync_all_done": "Toutes les playlists ont été mises à jour !",
        "notif_sched_item": "⏰ [Auto] Playlist « {nom} » mise à jour avec succès ({status})."
    },
    "en": {
        "subtitle": "Xtream Codes credentials & expiration date tracker",
        "add_playlist": "Add playlist",
        "refresh_all": "Refresh all",
        "settings_btn": "Settings",
        "logout": "Logout",
        "no_playlist": "No playlist saved in your workspace.",
        "no_playlist_sub": "Click the button below to add your first playlist using an M3U link or Xtream credentials.",
        "add_first": "Add my first playlist",
        "sync_card": "Synchronize this playlist",
        "edit": "Edit",
        "delete": "Delete",
        "confirm_delete": "Delete playlist",
        "server": "Server",
        "username": "Username",
        "password_hover": "Password (Hover)",
        "copy_btn": "Copy",
        "copied": "✓ Copied!",
        "expiration": "Expiration:",
        "time_left": "Time remaining:",
        "active_cons": "Active connections:",
        "last_sync": "Last sync:",
        "never": "Never",
        "copy_m3u": "Copy full M3U URL",
        "modal_add_title": "Add playlist",
        "modal_edit_title": "Edit playlist",
        "playlist_name": "Playlist / Relative name *",
        "playlist_name_ph": "E.g., Living Room, Parents, Brother...",
        "quick_fill": "⚡ Auto-fill via M3U link (Optional)",
        "quick_fill_ph": "Paste http://.../get.php?username=... link here",
        "quick_fill_help": "Automatically extracts server, username, and password.",
        "server_label": "Server *",
        "username_label": "Username *",
        "password_label": "Password *",
        "gotify_toggle": "🔔 Enable Gotify notifications for this playlist",
        "gotify_url": "Gotify server URL (e.g., http://192.168.1.3:8080)",
        "gotify_token": "Gotify application token",
        "gotify_days": "Alert when X days remaining",
        "gotify_freq": "Repeat alert every X days",
        "gotify_custom_msg": "Custom message (Optional - Variables: {nom}, {days}, {date})",
        "gotify_custom_ph": "Leave empty to use the default translated message",
        "gotify_test_btn": "📡 Test Gotify notification",
        "gotify_testing": "Sending...",
        "gotify_test_ok": "✓ Notification received on Gotify!",
        "gotify_test_err": "❌ Failed: check URL and Token",
        "gotify_alert_title": "⚠️ IPTV Expiration: {nom}",
        "gotify_alert_body": "Playlist '{nom}' expires in {days} days (on {date}).",
        "gotify_test_title": "🔔 M3U-Monitor Test: {nom}",
        "gotify_test_body": "Gotify connection successful for playlist '{nom}'!",
        "cancel": "Cancel",
        "save": "Save",
        "status_active": "Active",
        "status_expired": "Expired",
        "status_invalid": "Invalid credentials",
        "status_unreachable": "Server unreachable",
        "status_unknown": "Unknown",
        "status_http_err": "HTTP Error",
        "unlimited": "Unlimited",
        "days": "days",
        "expired_days": "Expired ({days} d)",
        "at_time": "at",
        "setup_title": "M3U-Monitor Initial Setup",
        "setup_sub": "Create the first Administrator account to secure the application.",
        "login_title": "Sign In",
        "login_sub": "Access your personal IPTV playlists",
        "register_title": "Create Account",
        "register_sub": "Create your personal workspace to track your playlists",
        "user_field": "Username",
        "pass_field": "Password",
        "login_btn": "Sign in",
        "register_btn": "Sign up",
        "setup_btn": "Create Administrator account",
        "no_account_yet": "Don't have an account?",
        "create_account_link": "Create an account",
        "already_account": "Already have an account?",
        "login_link": "Sign in",
        "err_invalid_login": "Invalid username or password.",
        "err_user_exists": "This username is already taken.",
        "err_reg_disabled": "Public registration is disabled by the administrator.",
        "settings_title": "Settings",
        "tab_general": "Language",
        "tab_scheduler": "Auto-Update",
        "tab_users": "Users",
        "tab_about": "About",
        "choose_lang": "Interface Language",
        "sched_enable": "Enable automatic background check",
        "sched_every_days": "Check playlists every (days):",
        "sched_at_time": "Execution time (HH:MM):",
        "sched_last_run": "Last automatic run:",
        "sched_run_now": "⚡ Test scheduler now",
        "sched_save": "Save schedule",
        "allow_reg_label": "Allow new user registration on the login page",
        "add_user_section": "Create a new user",
        "role_admin": "Admin",
        "role_user": "User",
        "create_user_btn": "Add",
        "confirm_del_user": "Delete this user and all their playlists?",
        "about_desc": "Lightweight Xtream Codes / M3U credentials & expiration manager.",
        "about_version": "Installed version",
        "about_dev": "Built with",
        "about_github": "GitHub Repository",
        "notif_center": "Notifications",
        "notif_clear": "Clear all",
        "notif_empty": "No notifications yet.",
        "toast_sync_start": "Refreshing playlist '{nom}'...",
        "toast_sync_done": "Playlist '{nom}' updated successfully ({status} - Conns: {cons}).",
        "toast_sync_err": "Error while refreshing '{nom}'.",
        "toast_sync_all_start": "Refreshing all playlists...",
        "toast_sync_all_done": "All playlists have been updated!",
        "notif_sched_item": "⏰ [Auto] Playlist '{nom}' updated successfully ({status})."
    },
    "es": {
        "subtitle": "Seguimiento de credenciales y fechas de vencimiento Xtream Codes",
        "add_playlist": "Añadir lista",
        "refresh_all": "Actualizar todo",
        "settings_btn": "Ajustes",
        "logout": "Cerrar sesión",
        "no_playlist": "No hay listas registradas en tu espacio.",
        "no_playlist_sub": "Haz clic en el botón de abajo para añadir tu primera lista mediante un enlace M3U o credenciales Xtream.",
        "add_first": "Añadir mi primera lista",
        "sync_card": "Sincronizar esta lista",
        "edit": "Editar",
        "delete": "Eliminar",
        "confirm_delete": "¿Eliminar la lista",
        "server": "Servidor",
        "username": "Usuario",
        "password_hover": "Contraseña (Pasar el ratón)",
        "copy_btn": "Copiar",
        "copied": "✓ ¡Copiado!",
        "expiration": "Vencimiento:",
        "time_left": "Tiempo restante:",
        "active_cons": "Conexiones activas:",
        "last_sync": "Última act.:",
        "never": "Nunca",
        "copy_m3u": "Copiar URL M3U completa",
        "modal_add_title": "Añadir una lista",
        "modal_edit_title": "Editar la lista",
        "playlist_name": "Nombre de la lista / Familiar *",
        "playlist_name_ph": "Ej: Salón, Padres, Hermano...",
        "quick_fill": "⚡ Autocompletar con enlace M3U (Opcional)",
        "quick_fill_ph": "Pega el enlace http://.../get.php?username=... aquí",
        "quick_fill_help": "Extrae automáticamente el servidor, el usuario y la contraseña.",
        "server_label": "Servidor *",
        "username_label": "Usuario *",
        "password_label": "Contraseña *",
        "gotify_toggle": "🔔 Activar notificaciones Gotify para esta lista",
        "gotify_url": "URL del servidor Gotify (ej: http://192.168.1.3:8080)",
        "gotify_token": "Token de la aplicación Gotify",
        "gotify_days": "Avisar cuando queden X días",
        "gotify_freq": "Repetir alerta cada X días",
        "gotify_custom_msg": "Mensaje personalizado (Opcional - Variables: {nom}, {days}, {date})",
        "gotify_custom_ph": "Dejar vacío para usar el mensaje traducido por defecto",
        "gotify_test_btn": "📡 Probar notificación Gotify",
        "gotify_testing": "Enviando...",
        "gotify_test_ok": "✓ ¡Notificación recibida en Gotify!",
        "gotify_test_err": "❌ Error: verifica la URL y el Token",
        "gotify_alert_title": "⚠️ Vencimiento IPTV: {nom}",
        "gotify_alert_body": "La lista '{nom}' vence en {days} días (el {date}).",
        "gotify_test_title": "🔔 Prueba M3U-Monitor: {nom}",
        "gotify_test_body": "¡Conexión Gotify exitosa para la lista '{nom}'!",
        "cancel": "Cancelar",
        "save": "Guardar",
        "status_active": "Activo",
        "status_expired": "Caducado",
        "status_invalid": "Credenciales inválidas",
        "status_unreachable": "Servidor inaccesible",
        "status_unknown": "Desconocido",
        "status_http_err": "Error HTTP",
        "unlimited": "Ilimitado",
        "days": "días",
        "expired_days": "Caducado ({days} d)",
        "at_time": "a las",
        "setup_title": "Configuración inicial de M3U-Monitor",
        "setup_sub": "Crea la primera cuenta de Administrador para proteger la aplicación.",
        "login_title": "Iniciar sesión",
        "login_sub": "Accede a tus listas IPTV personales",
        "register_title": "Crear una cuenta",
        "register_sub": "Crea tu espacio personal para gestionar tus listas",
        "user_field": "Nombre de usuario",
        "pass_field": "Contraseña",
        "login_btn": "Entrar",
        "register_btn": "Registrarse",
        "setup_btn": "Crear cuenta de Administrador",
        "no_account_yet": "¿Aún no tienes cuenta?",
        "create_account_link": "Crear una cuenta",
        "already_account": "¿Ya tienes una cuenta?",
        "login_link": "Iniciar sesión",
        "err_invalid_login": "Usuario o contraseña incorrectos.",
        "err_user_exists": "Este nombre de usuario ya existe.",
        "err_reg_disabled": "El registro público está desactivado por el administrador.",
        "settings_title": "Ajustes",
        "tab_general": "Idioma",
        "tab_scheduler": "Auto-Actualización",
        "tab_users": "Usuarios",
        "tab_about": "Acerca de",
        "choose_lang": "Idioma de la interfaz",
        "sched_enable": "Activar comprobación automática en segundo plano",
        "sched_every_days": "Comprobar listas cada (días):",
        "sched_at_time": "Hora de ejecución (HH:MM):",
        "sched_last_run": "Última ejecución automática:",
        "sched_run_now": "⚡ Probar programador ahora",
        "sched_save": "Guardar programación",
        "allow_reg_label": "Permitir el registro de nuevos usuarios en la página de acceso",
        "add_user_section": "Crear un nuevo usuario",
        "role_admin": "Admin",
        "role_user": "Usuario",
        "create_user_btn": "Añadir",
        "confirm_del_user": "¿Eliminar este usuario y todas sus listas?",
        "about_desc": "Gestor ligero de credenciales y vencimientos Xtream Codes / M3U.",
        "about_version": "Versión instalada",
        "about_dev": "Desarrollado con",
        "about_github": "Proyecto en GitHub",
        "notif_center": "Notificaciones",
        "notif_clear": "Borrar todo",
        "notif_empty": "No hay notificaciones por el momento.",
        "toast_sync_start": "Actualizando la lista « {nom} »...",
        "toast_sync_done": "Lista « {nom} » actualizada con éxito ({status} - Conexiones: {cons}).",
        "toast_sync_err": "Error al actualizar « {nom} ».",
        "toast_sync_all_start": "Actualizando todas las listas...",
        "toast_sync_all_done": "¡Todas las listas han sido actualizadas!",
        "notif_sched_item": "⏰ [Auto] Lista « {nom} » actualizada con éxito ({status})."
    },
    "de": {
        "subtitle": "Xtream Codes Zugangsdaten & Ablaufdatum-Tracker",
        "add_playlist": "Playlist hinzufügen",
        "refresh_all": "Alle aktualisieren",
        "settings_btn": "Einstellungen",
        "logout": "Abmelden",
        "no_playlist": "Keine Playlist in Ihrem Bereich gespeichert.",
        "no_playlist_sub": "Klicken Sie unten, um Ihre erste Liste über einen M3U-Link hinzuzufügen.",
        "add_first": "Erste Playlist hinzufügen",
        "sync_card": "Diese Playlist synchronisieren",
        "edit": "Bearbeiten",
        "delete": "Löschen",
        "confirm_delete": "Playlist löschen",
        "server": "Server",
        "username": "Benutzername",
        "password_hover": "Passwort (Hover)",
        "copy_btn": "Kopieren",
        "copied": "✓ Kopiert!",
        "expiration": "Ablaufdatum:",
        "time_left": "Verbleibende Zeit:",
        "active_cons": "Aktive Verbindungen:",
        "last_sync": "Letztes Update:",
        "never": "Nie",
        "copy_m3u": "Vollständige M3U-URL kopieren",
        "modal_add_title": "Playlist hinzufügen",
        "modal_edit_title": "Playlist bearbeiten",
        "playlist_name": "Playlist-Name / Kontakt *",
        "playlist_name_ph": "Z.B. Wohnzimmer, Eltern, Bruder...",
        "quick_fill": "⚡ Auto-Ausfüllen über M3U-Link (Optional)",
        "quick_fill_ph": "Hier http://.../get.php?username=... einfügen",
        "quick_fill_help": "Extrahiert automatisch Server, Benutzername und Passwort.",
        "server_label": "Server *",
        "username_label": "Benutzername *",
        "password_label": "Passwort *",
        "gotify_toggle": "🔔 Gotify-Benachrichtigungen für diese Playlist aktivieren",
        "gotify_url": "Gotify Server-URL (z.B. http://192.168.1.3:8080)",
        "gotify_token": "Gotify App-Token",
        "gotify_days": "Warnen ab X verbleibenden Tagen",
        "gotify_freq": "Alarm alle X Tage wiederholen",
        "gotify_custom_msg": "Eigene Nachricht (Optional - Variablen: {nom}, {days}, {date})",
        "gotify_custom_ph": "Leer lassen für die übersetzte Standardnachricht",
        "gotify_test_btn": "📡 Gotify-Benachrichtigung testen",
        "gotify_testing": "Wird gesendet...",
        "gotify_test_ok": "✓ Benachrichtigung auf Gotify empfangen!",
        "gotify_test_err": "❌ Fehler: URL und Token prüfen",
        "gotify_alert_title": "⚠️ IPTV Ablauf: {nom}",
        "gotify_alert_body": "Die Playlist '{nom}' läuft in {days} Tagen ab (am {date}).",
        "gotify_test_title": "🔔 M3U-Monitor Test: {nom}",
        "gotify_test_body": "Gotify-Verbindung erfolgreich für Playlist '{nom}'!",
        "cancel": "Abbrechen",
        "save": "Speichern",
        "status_active": "Aktiv",
        "status_expired": "Abgelaufen",
        "status_invalid": "Ungültige Anmeldeinformationen",
        "status_unreachable": "Server nicht erreichbar",
        "status_unknown": "Unbekannt",
        "status_http_err": "HTTP-Fehler",
        "unlimited": "Unbegrenzt",
        "days": "Tage",
        "expired_days": "Abgelaufen ({days} T)",
        "at_time": "um",
        "setup_title": "M3U-Monitor Ersteinrichtung",
        "setup_sub": "Erstellen Sie das erste Administrator-Konto.",
        "login_title": "Anmelden",
        "login_sub": "Greifen Sie auf Ihre persönlichen IPTV-Playlists zu",
        "register_title": "Konto erstellen",
        "register_sub": "Erstellen Sie Ihren persönlichen Bereich",
        "user_field": "Benutzername",
        "pass_field": "Passwort",
        "login_btn": "Anmelden",
        "register_btn": "Registrieren",
        "setup_btn": "Administrator-Konto erstellen",
        "no_account_yet": "Noch kein Konto?",
        "create_account_link": "Konto erstellen",
        "already_account": "Bereits ein Konto?",
        "login_link": "Anmelden",
        "err_invalid_login": "Ungültiger Benutzername oder Passwort.",
        "err_user_exists": "Dieser Benutzername ist bereits vergeben.",
        "err_reg_disabled": "Öffentliche Registrierung ist deaktiviert.",
        "settings_title": "Einstellungen",
        "tab_general": "Sprache",
        "tab_scheduler": "Auto-Update",
        "tab_users": "Benutzer",
        "tab_about": "Über",
        "choose_lang": "Sprache der Benutzeroberfläche",
        "sched_enable": "Automatische Hintergrundprüfung aktivieren",
        "sched_every_days": "Playlists prüfen alle (Tage):",
        "sched_at_time": "Ausführungszeit (HH:MM):",
        "sched_last_run": "Letzter automatischer Lauf:",
        "sched_run_now": "⚡ Zeitplan jetzt testen",
        "sched_save": "Zeitplan speichern",
        "allow_reg_label": "Registrierung auf der Anmeldeseite erlauben",
        "add_user_section": "Neuen Benutzer erstellen",
        "role_admin": "Admin",
        "role_user": "Benutzer",
        "create_user_btn": "Hinzufügen",
        "confirm_del_user": "Diesen Benutzer und alle Playlists löschen?",
        "about_desc": "Leichtgewichtiger Xtream Codes / M3U Zugangsdaten- & Ablauf-Manager.",
        "about_version": "Installierte Version",
        "about_dev": "Entwickelt mit",
        "about_github": "GitHub-Projekt",
        "notif_center": "Benachrichtigungen",
        "notif_clear": "Alle löschen",
        "notif_empty": "Noch keine Benachrichtigungen.",
        "toast_sync_start": "Playlist « {nom} » wird aktualisiert...",
        "toast_sync_done": "Playlist « {nom} » erfolgreich aktualisiert ({status} - Verb.: {cons}).",
        "toast_sync_err": "Fehler beim Aktualisieren von « {nom} ».",
        "toast_sync_all_start": "Alle Playlists werden aktualisiert...",
        "toast_sync_all_done": "Alle Playlists wurden aktualisiert!",
        "notif_sched_item": "⏰ [Auto] Playlist « {nom} » erfolgreich aktualisiert ({status})."
    }
}

def get_lang():
    lang = session.get("lang", "fr")
    return lang if lang in TRANSLATIONS else "fr"

def load_settings():
    os.makedirs(DATA_DIR, exist_ok=True)
    default_settings = {
        "allow_registration": True,
        "schedule_enabled": True,
        "schedule_every_days": 1,
        "schedule_time": "02:00",
        "last_scheduled_run": None
    }
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=2)
        return default_settings
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default_settings, **data}
    except Exception:
        return default_settings

def save_settings(settings):
    os.makedirs(DATA_DIR, exist_ok=True)
    with file_lock:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

def load_users():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_PATH):
        return []
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_users(users):
    os.makedirs(DATA_DIR, exist_ok=True)
    with file_lock:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

def load_notifications(user_id=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(NOTIFS_PATH):
        return []
    try:
        with open(NOTIFS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if user_id:
                return [n for n in data if n.get("user_id") in (user_id, "all")]
            return data
    except Exception:
        return []

def add_notification(user_id, message, level="info"):
    os.makedirs(DATA_DIR, exist_ok=True)
    with file_lock:
        notifs = []
        if os.path.exists(NOTIFS_PATH):
            try:
                with open(NOTIFS_PATH, "r", encoding="utf-8") as f:
                    notifs = json.load(f)
            except Exception:
                notifs = []
        notifs.insert(0, {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "message": message,
            "level": level,
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        })
        notifs = notifs[:100]
        with open(NOTIFS_PATH, "w", encoding="utf-8") as f:
            json.dump(notifs, f, indent=2, ensure_ascii=False)

def clear_user_notifications(user_id):
    os.makedirs(DATA_DIR, exist_ok=True)
    with file_lock:
        if not os.path.exists(NOTIFS_PATH):
            return
        try:
            with open(NOTIFS_PATH, "r", encoding="utf-8") as f:
                notifs = json.load(f)
            notifs = [n for n in notifs if n.get("user_id") not in (user_id, "all")]
            with open(NOTIFS_PATH, "w", encoding="utf-8") as f:
                json.dump(notifs, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def load_all_accounts(default_owner_id=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ACCOUNTS_PATH):
        with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []
    try:
        with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            modified = False
            for item in data:
                if "id" not in item or not item["id"]:
                    item["id"] = str(uuid.uuid4())
                    modified = True
                if not item.get("owner_id") and default_owner_id:
                    item["owner_id"] = default_owner_id
                    modified = True
                raw_pw = item.get("password", "")
                if raw_pw and not raw_pw.startswith("enc:"):
                    item["password"] = encrypt_str(raw_pw)
                    modified = True
                if "gotify_enabled" not in item:
                    item["gotify_enabled"] = False
                    item["gotify_url"] = ""
                    item["gotify_token"] = ""
                    item["gotify_days"] = 30
                    item["gotify_freq"] = 3
                    item["gotify_custom_msg"] = ""
                    item["last_gotify_date"] = None
                    modified = True
                if "gotify_custom_msg" not in item:
                    item["gotify_custom_msg"] = ""
                    modified = True
                if "last_sync" not in item:
                    item["last_sync"] = None
                    modified = True
                if "cached_info" not in item:
                    item["cached_info"] = None
                    modified = True
            if modified:
                save_all_accounts(data)
            return data
    except Exception:
        return []

def save_all_accounts(accounts):
    os.makedirs(DATA_DIR, exist_ok=True)
    with file_lock:
        with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)

def send_gotify_alert(url, token, title, message):
    if not url or not token:
        return False
    try:
        r = requests.post(
            f"{url.strip().rstrip('/')}/message?token={token.strip()}",
            json={"title": title, "message": message, "priority": 5},
            timeout=5
        )
        return r.status_code == 200
    except Exception:
        return False

def format_gotify_message(custom_msg, default_tpl, nom, days, date_str):
    tpl = custom_msg.strip() if custom_msg and custom_msg.strip() else default_tpl
    try:
        return tpl.replace("{nom}", str(nom)).replace("{days}", str(days)).replace("{date}", str(date_str))
    except Exception:
        return default_tpl

def get_status_label_from_info(info, t):
    state = (info or {}).get("state", "unknown")
    if state == "active":
        return t["status_active"]
    elif state == "expired":
        return t["status_expired"]
    elif state == "invalid":
        return t["status_invalid"]
    elif state == "unreachable":
        return t["status_unreachable"]
    elif state == "http_err":
        return f"{t['status_http_err']} {info.get('http_code', '')}"
    elif state == "other":
        return info.get("raw_status", t["status_unknown"])
    return t["status_unknown"]

def fetch_live_xtream_info(acc):
    host = acc.get("host", "").strip().rstrip("/")
    username = acc.get("username", "").strip()
    password = decrypt_str(acc.get("password", "").strip())
    nom = acc.get("nom", "Playlist").strip()
    acc_id = acc.get("id")

    # Paramètre anti-cache (_t) + fermeture immédiate du socket TCP pour éviter les sessions fantômes et le cache CDN
    cache_buster = int(time.time() * 1000)
    api_url = f"{host}/player_api.php?username={username}&password={password}&_t={cache_buster}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) M3U-Monitor/0.4",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Connection": "close"
    }
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    info = {
        "state": "unknown",
        "raw_status": "Unknown",
        "exp_timestamp": None,
        "active_cons": "-",
        "max_cons": "-",
        "http_code": None
    }

    try:
        with requests.get(api_url, headers=headers, timeout=8) as r:
            if r.status_code == 200:
                data = r.json()
                user_info = data.get("user_info", {})
                if user_info.get("auth") == 0:
                    info["state"] = "invalid"
                else:
                    status = user_info.get("status", "Unknown")
                    info["raw_status"] = status
                    info["active_cons"] = str(user_info.get("active_cons", "0"))
                    info["max_cons"] = str(user_info.get("max_connections", "0"))
                    info["exp_timestamp"] = user_info.get("exp_date")
                    if status == "Active":
                        info["state"] = "active"
                    elif status == "Expired":
                        info["state"] = "expired"
                    else:
                        info["state"] = "other"
            else:
                info["state"] = "http_err"
                info["http_code"] = r.status_code
    except Exception:
        info["state"] = "unreachable"

    exp_ts = info.get("exp_timestamp")
    gotify_sent_date = None
    if exp_ts and str(exp_ts).isdigit():
        exp_dt = datetime.fromtimestamp(int(exp_ts))
        days_left = (exp_dt - datetime.now()).days
        if 0 <= days_left <= int(acc.get("gotify_days", 30)):
            if acc.get("gotify_enabled") and acc.get("gotify_url") and acc.get("gotify_token"):
                last_alert = acc.get("last_gotify_date")
                freq = int(acc.get("gotify_freq", 3))
                should_alert = True
                if last_alert:
                    try:
                        last_dt = datetime.strptime(last_alert, "%Y-%m-%d")
                        if (datetime.now() - last_dt).days < freq:
                            should_alert = False
                    except Exception:
                        pass
                if should_alert:
                    t_fr = TRANSLATIONS["fr"]
                    date_short = exp_dt.strftime("%d/%m/%Y")
                    title_msg = t_fr["gotify_alert_title"].format(nom=nom)
                    body_msg = format_gotify_message(
                        acc.get("gotify_custom_msg", ""),
                        t_fr["gotify_alert_body"],
                        nom,
                        days_left,
                        date_short
                    )
                    if send_gotify_alert(acc.get("gotify_url"), acc.get("gotify_token"), title_msg, body_msg):
                        gotify_sent_date = datetime.now().strftime("%Y-%m-%d")

    all_accs = load_all_accounts()
    for item in all_accs:
        if item.get("id") == acc_id:
            item["cached_info"] = info
            item["last_sync"] = now_str
            if gotify_sent_date:
                item["last_gotify_date"] = gotify_sent_date
            break
    save_all_accounts(all_accs)
    acc["cached_info"] = info
    acc["last_sync"] = now_str
    return acc

def build_account_view(acc, t, force_refresh=False):
    if force_refresh or not acc.get("cached_info"):
        acc = fetch_live_xtream_info(acc)

    acc_id = acc.get("id", str(uuid.uuid4()))
    host = acc.get("host", "").strip().rstrip("/")
    username = acc.get("username", "").strip()
    password = decrypt_str(acc.get("password", "").strip())
    nom = acc.get("nom", "Playlist").strip()
    info = acc.get("cached_info") or {}

    res = {
        "id": acc_id,
        "nom": nom,
        "host": host,
        "username": username,
        "password": password,
        "gotify_enabled": acc.get("gotify_enabled", False),
        "gotify_url": acc.get("gotify_url", ""),
        "gotify_token": acc.get("gotify_token", ""),
        "gotify_days": acc.get("gotify_days", 30),
        "gotify_freq": acc.get("gotify_freq", 3),
        "gotify_custom_msg": acc.get("gotify_custom_msg", ""),
        "last_sync": acc.get("last_sync") or t["never"],
        "m3u_url": f"{host}/get.php?username={username}&password={password}&type=m3u_plus&output=ts",
        "status_label": t["status_unknown"],
        "badge_class": "bg-slate-700 text-slate-300",
        "exp_date_str": "N/A",
        "days_left_str": "N/A",
        "days_class": "text-slate-400",
        "active_cons": info.get("active_cons", "-"),
        "max_cons": info.get("max_cons", "-")
    }

    state = info.get("state", "unknown")
    if state == "invalid":
        res["status_label"] = t["status_invalid"]
        res["badge_class"] = "bg-red-900/70 text-red-300 border border-red-700"
        return res
    elif state == "unreachable":
        res["status_label"] = t["status_unreachable"]
        res["badge_class"] = "bg-red-900/60 text-red-300 border border-red-700"
        return res
    elif state == "http_err":
        res["status_label"] = f"{t['status_http_err']} {info.get('http_code', '')}"
        res["badge_class"] = "bg-amber-900/60 text-amber-300 border border-amber-700"
        return res
    elif state == "active":
        res["status_label"] = t["status_active"]
        res["badge_class"] = "bg-emerald-900/60 text-emerald-300 border border-emerald-700"
    elif state == "expired":
        res["status_label"] = t["status_expired"]
        res["badge_class"] = "bg-red-900/60 text-red-300 border border-red-700"
    elif state == "other":
        res["status_label"] = info.get("raw_status", t["status_unknown"])
        res["badge_class"] = "bg-amber-900/60 text-amber-300 border border-amber-700"

    exp_timestamp = info.get("exp_timestamp")
    if exp_timestamp and str(exp_timestamp).isdigit():
        exp_dt = datetime.fromtimestamp(int(exp_timestamp))
        res["exp_date_str"] = exp_dt.strftime(f"%d/%m/%Y {t['at_time']} %H:%M")
        days_left = (exp_dt - datetime.now()).days

        if days_left < 0:
            res["days_left_str"] = t["expired_days"].format(days=abs(days_left))
            res["days_class"] = "text-red-400"
        elif days_left <= int(acc.get("gotify_days", 30)):
            res["days_left_str"] = f"{days_left} {t['days']} ⚠️"
            res["days_class"] = "text-amber-400"
        else:
            res["days_left_str"] = f"{days_left} {t['days']}"
            res["days_class"] = "text-emerald-400"
    elif exp_timestamp is None and state == "active":
        res["exp_date_str"] = t["unlimited"]
        res["days_left_str"] = "∞"
        res["days_class"] = "text-emerald-400"

    return res

def execute_scheduled_sync_job(lang_code="fr"):
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS["fr"])
    all_accs = load_all_accounts()
    for acc in all_accs:
        updated_acc = fetch_live_xtream_info(acc)
        status_lbl = get_status_label_from_info(updated_acc.get("cached_info"), t)
        owner = updated_acc.get("owner_id") or "all"
        notif_msg = t["notif_sched_item"].format(nom=updated_acc.get("nom", "Playlist"), status=status_lbl)
        add_notification(owner, notif_msg, "success")

    settings = load_settings()
    settings["last_scheduled_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_settings(settings)
    return len(all_accs)

def background_scheduler_loop():
    os.makedirs(DATA_DIR, exist_ok=True)
    lock_file = open(SCHED_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        return

    while True:
        try:
            settings = load_settings()
            if settings.get("schedule_enabled", True):
                target_time = settings.get("schedule_time", "02:00")
                every_days = max(1, int(settings.get("schedule_every_days", 1)))
                now = datetime.now()
                current_hm = now.strftime("%H:%M")

                if current_hm == target_time:
                    last_run_str = settings.get("last_scheduled_run")
                    should_run = True
                    if last_run_str:
                        try:
                            last_dt = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M")
                            if (now - last_dt) < timedelta(days=every_days - 0.05):
                                should_run = False
                        except Exception:
                            pass

                    if should_run:
                        execute_scheduled_sync_job("fr")
        except Exception:
            pass
        time.sleep(20)

sched_thread = threading.Thread(target=background_scheduler_loop, daemon=True)
sched_thread.start()

def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    for u in load_users():
        if u.get("id") == uid:
            return u
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        users = load_users()
        if not users:
            return redirect(url_for("setup"))
        if not get_current_user():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

LOGO_COMPONENT = """
<div class="flex items-center gap-3 select-none">
    <img src="/logo" onerror="this.style.display='none'; document.getElementById('svg_fallback_logo').classList.remove('hidden');"
         alt="M3U-Monitor" class="h-14 w-auto rounded-xl object-contain shadow-md">
    <div id="svg_fallback_logo" class="hidden flex items-center gap-2.5">
        <svg class="w-12 h-12 shrink-0" viewBox="0 0 120 110" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="42" y1="22" x2="28" y2="6" stroke="#b45309" stroke-width="4" stroke-linecap="round"/>
            <circle cx="26" cy="5" r="4.5" fill="#b45309"/>
            <line x1="62" y1="22" x2="78" y2="6" stroke="#b45309" stroke-width="4" stroke-linecap="round"/>
            <circle cx="80" cy="5" r="4.5" fill="#b45309"/>
            <rect x="12" y="22" width="82" height="62" rx="14" fill="#271705" stroke="#b45309" stroke-width="5"/>
            <rect x="20" y="30" width="54" height="46" rx="8" fill="#180e02" stroke="#78350f" stroke-width="2"/>
            <polygon points="40,42 40,64 60,53" fill="#f97316"/>
            <circle cx="83" cy="39" r="3.5" fill="#f97316"/>
            <circle cx="83" cy="50" r="3.5" fill="#f97316"/>
            <line x1="28" y1="84" x2="22" y2="96" stroke="#b45309" stroke-width="5" stroke-linecap="round"/>
            <line x1="74" y1="84" x2="80" y2="96" stroke="#b45309" stroke-width="5" stroke-linecap="round"/>
            <rect x="65" y="52" width="38" height="38" rx="8" fill="#fef3c7" stroke="#f97316" stroke-width="3"/>
            <path d="M65 62 C65 56, 103 56, 103 62" fill="#f97316"/>
            <line x1="74" y1="49" x2="74" y2="56" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>
            <line x1="94" y1="49" x2="94" y2="56" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>
            <line x1="72" y1="69" x2="88" y2="69" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
            <line x1="72" y1="76" x2="85" y2="76" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
            <line x1="72" y1="83" x2="82" y2="83" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
            <circle cx="98" cy="84" r="14" fill="#f97316" stroke="#fef3c7" stroke-width="2.5"/>
            <polyline points="98,76 98,84 104,88" stroke="#fef3c7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div class="text-2xl font-extrabold tracking-tight">
            <span class="text-amber-700">M3u-</span><span class="text-orange-500">Monitor</span>
        </div>
    </div>
</div>
"""

FLAGS_SVG = {
    "fr": '<svg class="w-5 h-3.5 rounded-sm shadow-sm shrink-0" viewBox="0 0 3 2"><rect width="1" height="2" fill="#002395"/><rect width="1" height="2" x="1" fill="#fff"/><rect width="1" height="2" x="2" fill="#ED2939"/></svg>',
    "en": '<svg class="w-5 h-3.5 rounded-sm shadow-sm shrink-0" viewBox="0 0 60 30"><rect width="60" height="30" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="2"/><path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/><path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></svg>',
    "es": '<svg class="w-5 h-3.5 rounded-sm shadow-sm shrink-0" viewBox="0 0 3 2"><rect width="3" height="2" fill="#AA151B"/><rect width="3" height="1" y="0.5" fill="#F1BF00"/></svg>',
    "de": '<svg class="w-5 h-3.5 rounded-sm shadow-sm shrink-0" viewBox="0 0 5 3"><rect width="5" height="3" fill="#000"/><rect width="5" height="2" y="1" fill="#D00"/><rect width="5" height="1" y="2" fill="#FFCE00"/></svg>'
}

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M3U-Monitor</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
    <link rel="apple-touch-icon" href="/favicon.svg">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body { background-color: #0f172a; color: #f8fafc; }</style>
</head>
<body class="p-4 md:p-8 min-h-screen flex flex-col justify-between">
    <div class="max-w-7xl w-full mx-auto flex justify-between items-center">
        """ + LOGO_COMPONENT + """
        <div class="flex items-center gap-1.5 bg-slate-800/90 border border-slate-700 p-1 rounded-xl">
            {% for code, label in [('fr','Français'), ('en','English'), ('es','Español'), ('de','Deutsch')] %}
            <form action="/set-lang" method="POST" class="inline">
                <input type="hidden" name="lang" value="{{ code }}">
                <button type="submit" title="{{ label }}" class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition {% if lang == code %}bg-indigo-600 text-white shadow{% else %}text-slate-300 hover:bg-slate-700{% endif %}">
                    {{ flags[code] | safe }}
                    <span class="hidden sm:inline">{{ label }}</span>
                </button>
            </form>
            {% endfor %}
        </div>
    </div>

    <div class="max-w-md w-full mx-auto bg-slate-800/90 border border-slate-700 rounded-2xl p-6 md:p-8 shadow-2xl my-auto">
        <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-white">{{ title }}</h1>
            <p class="text-slate-400 text-sm mt-1">{{ subtitle }}</p>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}
                <div class="mb-4 bg-red-900/60 border border-red-700 text-red-200 text-xs px-3.5 py-2.5 rounded-lg">
                    {{ msg }}
                </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">{{ t.user_field }}</label>
                <input type="text" name="username" required autofocus
                       class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
            </div>
            <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">{{ t.pass_field }}</label>
                <input type="password" name="password" required
                       class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
            </div>
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white py-2.5 rounded-lg text-sm font-semibold transition shadow mt-2">
                {{ btn_label }}
            </button>
        </form>

        {% if mode == 'login' and allow_registration %}
        <div class="mt-6 pt-4 border-t border-slate-700/80 text-center text-xs text-slate-400">
            {{ t.no_account_yet }}
            <a href="/register" class="text-indigo-400 hover:text-indigo-300 font-semibold ml-1">{{ t.create_account_link }}</a>
        </div>
        {% elif mode == 'register' %}
        <div class="mt-6 pt-4 border-t border-slate-700/80 text-center text-xs text-slate-400">
            {{ t.already_account }}
            <a href="/login" class="text-indigo-400 hover:text-indigo-300 font-semibold ml-1">{{ t.login_link }}</a>
        </div>
        {% endif %}
    </div>

    <div class="text-center text-xs text-slate-500">
        m3u-Monitor v{{ version }} — Built with <span class="text-indigo-400 font-semibold">{{ dev_name }}</span>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M3U-Monitor</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="shortcut icon" href="/favicon.ico">
    <link rel="apple-touch-icon" href="/favicon.svg">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: #f8fafc; }
        .blur-pass { filter: blur(5px); transition: filter 0.2s; }
        .blur-pass:hover { filter: blur(0px); }
        @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spinning { animation: spin-slow 0.8s linear infinite; display: inline-block; }
    </style>
</head>
<body class="p-4 md:p-8 min-h-screen flex flex-col justify-between">
    <!-- Toast Container -->
    <div id="toastContainer" class="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none"></div>

    <div class="max-w-7xl w-full mx-auto">
        <!-- Header -->
        <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-6 gap-4 border-b border-slate-800 pb-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-3">
                """ + LOGO_COMPONENT + """
                <div class="sm:border-l sm:border-slate-800 sm:pl-4">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-medium bg-slate-800 border border-slate-700 text-slate-300 px-2.5 py-0.5 rounded-full">
                            👤 {{ user.username }}
                        </span>
                    </div>
                    <p class="text-slate-400 text-xs mt-1">{{ t.subtitle }}</p>
                </div>
            </div>

            <div class="flex flex-wrap items-center gap-2.5 relative">
                <button type="button" onclick="openAddModal()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition shadow flex items-center gap-1.5">
                    ➕ {{ t.add_playlist }}
                </button>
                <button type="button" onclick="syncAllPlaylists(this)" class="bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition shadow flex items-center gap-1.5">
                    <span id="syncAllIcon" class="inline-block">🔄</span> {{ t.refresh_all }}
                </button>

                <!-- Cloche de Notifications -->
                <div class="relative">
                    <button type="button" onclick="toggleNotifDrawer()" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-1 relative" title="{{ t.notif_center }}">
                        🔔
                        <span id="notifBadge" class="{% if not notifications %}hidden{% endif %} bg-orange-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                            {{ notifications | length }}
                        </span>
                    </button>

                    <!-- Panneau déroulant Notifications -->
                    <div id="notifDrawer" class="hidden absolute right-0 mt-2 w-80 sm:w-96 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-40 overflow-hidden">
                        <div class="flex justify-between items-center px-4 py-3 bg-slate-900/90 border-b border-slate-700">
                            <span class="text-xs font-bold text-white uppercase tracking-wider">🔔 {{ t.notif_center }}</span>
                            <button type="button" onclick="clearNotifications()" class="text-[11px] text-red-400 hover:text-red-300 transition">
                                🗑️ {{ t.notif_clear }}
                            </button>
                        </div>
                        <div id="notifList" class="max-h-72 overflow-y-auto divide-y divide-slate-700/60">
                            {% if not notifications %}
                            <div class="p-6 text-center text-xs text-slate-400">{{ t.notif_empty }}</div>
                            {% else %}
                                {% for n in notifications %}
                                <div class="p-3 text-xs hover:bg-slate-700/40 transition">
                                    <div class="text-slate-200 font-medium">{{ n.message }}</div>
                                    <div class="text-[10px] text-slate-400 mt-1">{{ n.time }}</div>
                                </div>
                                {% endfor %}
                            {% endif %}
                        </div>
                    </div>
                </div>

                <!-- Bouton Paramètres Unifié -->
                <button type="button" onclick="openSettingsModal()" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-1.5">
                    ⚙️ {{ t.settings_btn }}
                </button>

                <a href="/logout" class="bg-red-950/60 hover:bg-red-900/70 border border-red-800/70 text-red-200 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition" title="{{ t.logout }}">
                    🚪 {{ t.logout }}
                </a>
            </div>
        </div>

        {% if not accounts %}
        <div class="bg-slate-800/60 border border-slate-700 rounded-xl p-10 text-center my-8">
            <p class="text-slate-300 text-lg mb-2">{{ t.no_playlist }}</p>
            <p class="text-slate-400 text-sm mb-6">{{ t.no_playlist_sub }}</p>
            <button type="button" onclick="openAddModal()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition shadow">
                ➕ {{ t.add_first }}
            </button>
        </div>
        {% endif %}

        <!-- Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {% for acc in accounts %}
            <div id="card-{{ acc.id }}" class="bg-slate-800/90 border border-slate-700 rounded-xl p-5 shadow-lg flex flex-col justify-between transition">
                <div>
                    <div class="flex justify-between items-start mb-4 gap-2">
                        <h2 class="text-lg font-bold text-white truncate flex items-center gap-1.5">
                            {{ acc.nom }}
                            {% if acc.gotify_enabled %}
                            <span title="Gotify" class="text-xs">🔔</span>
                            {% endif %}
                        </h2>
                        <div class="flex items-center gap-1 shrink-0">
                            <span id="badge-{{ acc.id }}" class="px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap {{ acc.badge_class }}">
                                {{ acc.status_label }}
                            </span>
                            <button type="button" data-id="{{ acc.id }}" data-nom="{{ acc.nom }}" onclick="syncSinglePlaylist(this)" title="{{ t.sync_card }}" class="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-slate-700 rounded-lg transition">
                                <span class="sync-icon inline-block">🔄</span>
                            </button>
                            <button type="button" onclick='openEditModal({{ acc | tojson | safe }})' title="{{ t.edit }}" class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition">
                                ✏️
                            </button>
                            <form action="/delete/{{ acc.id }}" method="POST" data-nom="{{ acc.nom }}" onsubmit="return confirm('{{ t.confirm_delete }} ' + this.dataset.nom + ' ?');" class="inline">
                                <button type="submit" title="{{ t.delete }}" class="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded-lg transition">
                                    🗑️
                                </button>
                            </form>
                        </div>
                    </div>

                    <div class="space-y-2.5 text-sm">
                        <div class="bg-slate-900/90 p-2.5 rounded-lg flex justify-between items-center border border-slate-800">
                            <div class="truncate pr-2">
                                <span class="text-slate-400 text-xs block">{{ t.server }}</span>
                                <span class="font-mono text-slate-200 text-xs">{{ acc.host }}</span>
                            </div>
                            <button type="button" data-copy="{{ acc.host }}" onclick="copyFromAttr(this)" class="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-2.5 py-1.5 rounded transition shrink-0">{{ t.copy_btn }}</button>
                        </div>

                        <div class="bg-slate-900/90 p-2.5 rounded-lg flex justify-between items-center border border-slate-800">
                            <div class="truncate pr-2">
                                <span class="text-slate-400 text-xs block">{{ t.username }}</span>
                                <span class="font-mono text-emerald-400 font-medium">{{ acc.username }}</span>
                            </div>
                            <button type="button" data-copy="{{ acc.username }}" onclick="copyFromAttr(this)" class="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-2.5 py-1.5 rounded transition shrink-0">{{ t.copy_btn }}</button>
                        </div>

                        <div class="bg-slate-900/90 p-2.5 rounded-lg flex justify-between items-center border border-slate-800">
                            <div class="truncate pr-2">
                                <span class="text-slate-400 text-xs block">{{ t.password_hover }}</span>
                                <span class="font-mono text-amber-400 font-medium blur-pass select-all">{{ acc.password }}</span>
                            </div>
                            <button type="button" data-copy="{{ acc.password }}" onclick="copyFromAttr(this)" class="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-2.5 py-1.5 rounded transition shrink-0">{{ t.copy_btn }}</button>
                        </div>
                    </div>
                </div>

                <div class="mt-5 pt-4 border-t border-slate-700/80 space-y-2 text-sm">
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400">{{ t.expiration }}</span>
                        <span id="exp-{{ acc.id }}" class="font-semibold text-slate-200">{{ acc.exp_date_str }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400">{{ t.time_left }}</span>
                        <span id="days-{{ acc.id }}" class="font-bold {{ acc.days_class }}">{{ acc.days_left_str }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400">{{ t.active_cons }}</span>
                        <span id="cons-{{ acc.id }}" class="font-mono text-slate-300">{{ acc.active_cons }} / {{ acc.max_cons }}</span>
                    </div>
                    <div class="flex justify-between items-center text-xs text-slate-400 pt-1">
                        <span>{{ t.last_sync }}</span>
                        <span id="sync-{{ acc.id }}" class="font-mono text-slate-300">{{ acc.last_sync }}</span>
                    </div>

                    <div class="pt-3 flex gap-2">
                        <button type="button" data-copy="{{ acc.m3u_url }}" onclick="copyFromAttr(this)" class="w-full bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded-lg text-xs font-medium transition">
                            🔗 {{ t.copy_m3u }}
                        </button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Footer Crédits -->
    <footer class="max-w-7xl w-full mx-auto mt-12 pt-6 border-t border-slate-800/80 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-slate-400">
        <div>
            <span class="font-bold text-slate-200">m3u-Monitor v{{ version }}</span> — Built with
            <span class="text-indigo-400 font-semibold">{{ dev_name }}</span>
        </div>
        <div class="flex items-center gap-4">
            <a href="{{ github_url }}" target="_blank" class="hover:text-white transition">⭐ GitHub</a>
        </div>
    </footer>

    <!-- Modal Ajout / Edition Playlist -->
    <div id="accountModal" class="fixed inset-0 bg-black/75 hidden items-center justify-center p-4 z-50 overflow-y-auto">
        <div class="bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full p-6 shadow-2xl my-8">
            <div class="flex justify-between items-center mb-4">
                <h3 id="modalTitle" class="text-lg font-bold text-white">{{ t.modal_add_title }}</h3>
                <button type="button" onclick="closeModal()" class="text-slate-400 hover:text-white text-xl">&times;</button>
            </div>

            <form action="/save" method="POST" class="space-y-4">
                <input type="hidden" name="id" id="field_id">

                <div>
                    <label class="block text-xs font-medium text-slate-300 mb-1">{{ t.playlist_name }}</label>
                    <input type="text" name="nom" id="field_nom" required placeholder="{{ t.playlist_name_ph }}"
                           class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                </div>

                <div class="bg-slate-900/70 p-3 rounded-lg border border-slate-700/80">
                    <label class="block text-xs font-semibold text-indigo-400 mb-1">{{ t.quick_fill }}</label>
                    <input type="text" id="field_m3u_paste" oninput="parseM3uUrl(this.value)" placeholder="{{ t.quick_fill_ph }}"
                           class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
                    <p class="text-[11px] text-slate-400 mt-1">{{ t.quick_fill_help }}</p>
                </div>

                <div>
                    <label class="block text-xs font-medium text-slate-300 mb-1">{{ t.server_label }}</label>
                    <input type="url" name="host" id="field_host" required placeholder="http://exemple-iptv.com:8080"
                           class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-indigo-500">
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">{{ t.username_label }}</label>
                        <input type="text" name="username" id="field_username" required placeholder="user123"
                               class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-indigo-500">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">{{ t.password_label }}</label>
                        <input type="text" name="password" id="field_password" required placeholder="pass123"
                               class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-indigo-500">
                    </div>
                </div>

                <!-- Section Gotify par playlist -->
                <div class="bg-slate-900/80 p-3.5 rounded-lg border border-slate-700 space-y-3">
                    <label class="flex items-center gap-2 text-xs font-medium text-slate-200 cursor-pointer">
                        <input type="checkbox" name="gotify_enabled" id="field_gotify_enabled" onchange="toggleGotifyFields(this.checked)"
                               class="w-4 h-4 accent-emerald-500 cursor-pointer">
                        {{ t.gotify_toggle }}
                    </label>

                    <div id="gotify_fields" class="space-y-2.5 hidden pt-2 border-t border-slate-800">
                        <div>
                            <label class="block text-[11px] text-slate-400 mb-1">{{ t.gotify_url }}</label>
                            <input type="url" name="gotify_url" id="field_gotify_url" placeholder="http://192.168.1.3:8080"
                                   class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono">
                        </div>
                        <div>
                            <label class="block text-[11px] text-slate-400 mb-1">{{ t.gotify_token }}</label>
                            <input type="text" name="gotify_token" id="field_gotify_token" placeholder="Axxxxxxxxxxxxx"
                                   class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono">
                        </div>
                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="block text-[10px] text-slate-400 mb-1">{{ t.gotify_days }}</label>
                                <input type="number" name="gotify_days" id="field_gotify_days" value="30" min="1" max="365"
                                       class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 text-center font-mono">
                            </div>
                            <div>
                                <label class="block text-[10px] text-slate-400 mb-1">{{ t.gotify_freq }}</label>
                                <input type="number" name="gotify_freq" id="field_gotify_freq" value="3" min="1" max="30"
                                       class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 text-center font-mono">
                            </div>
                        </div>
                        <div>
                            <label class="block text-[11px] text-slate-400 mb-1">{{ t.gotify_custom_msg }}</label>
                            <textarea name="gotify_custom_msg" id="field_gotify_custom_msg" rows="2" placeholder="{{ t.gotify_custom_ph }}"
                                      class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"></textarea>
                        </div>
                        <div class="pt-1">
                            <button type="button" id="gotify_test_btn" onclick="testGotify()"
                                    class="w-full bg-indigo-600/80 hover:bg-indigo-600 text-white py-1.5 px-3 rounded-lg text-xs font-medium transition">
                                {{ t.gotify_test_btn }}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="flex justify-end gap-2 pt-3 border-t border-slate-700">
                    <button type="button" onclick="closeModal()" class="px-4 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition">
                        {{ t.cancel }}
                    </button>
                    <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow">
                        💾 {{ t.save }}
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Modal Paramètres Unifié (Langue / Scheduler / Utilisateurs / À propos) -->
    <div id="settingsModal" class="fixed inset-0 bg-black/75 hidden items-center justify-center p-4 z-50 overflow-y-auto">
        <div class="bg-slate-800 border border-slate-700 rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-5 my-8">
            <div class="flex justify-between items-center border-b border-slate-700 pb-3">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">⚙️ {{ t.settings_title }}</h3>
                <button type="button" onclick="closeSettingsModal()" class="text-slate-400 hover:text-white text-xl">&times;</button>
            </div>

            <!-- Navigation par onglets -->
            <div class="flex flex-wrap gap-1.5 border-b border-slate-700 pb-3">
                <button type="button" onclick="switchSettingsTab('general')" id="tabbtn-general" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition">
                    🌐 {{ t.tab_general }}
                </button>
                <button type="button" onclick="switchSettingsTab('scheduler')" id="tabbtn-scheduler" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-slate-300 hover:bg-slate-700 transition">
                    ⏰ {{ t.tab_scheduler }}
                </button>
                {% if user.is_admin %}
                <button type="button" onclick="switchSettingsTab('users')" id="tabbtn-users" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-slate-300 hover:bg-slate-700 transition">
                    👥 {{ t.tab_users }}
                </button>
                {% endif %}
                <button type="button" onclick="switchSettingsTab('about')" id="tabbtn-about" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-slate-300 hover:bg-slate-700 transition">
                    ℹ️ {{ t.tab_about }}
                </button>
            </div>

            <!-- Onglet 1 : Langue avec vrais drapeaux SVG -->
            <div id="tab-general" class="space-y-4">
                <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider">{{ t.choose_lang }}</label>
                <div class="grid grid-cols-2 gap-3">
                    {% for code, label in [('fr','Français'), ('en','English'), ('es','Español'), ('de','Deutsch')] %}
                    <form action="/set-lang" method="POST">
                        <input type="hidden" name="lang" value="{{ code }}">
                        <button type="submit" class="w-full flex items-center gap-3 p-3 rounded-xl border text-sm font-medium transition {% if lang == code %}bg-indigo-600/20 border-indigo-500 text-white shadow{% else %}bg-slate-900/90 border-slate-800 text-slate-300 hover:bg-slate-700/60{% endif %}">
                            {{ flags[code] | safe }}
                            <span>{{ label }}</span>
                        </button>
                    </form>
                    {% endfor %}
                </div>
            </div>

            <!-- Onglet 2 : Planificateur automatique -->
            <div id="tab-scheduler" class="hidden space-y-4">
                <form action="/settings/scheduler" method="POST" class="space-y-4">
                    <label class="flex items-center justify-between bg-slate-900/80 p-3.5 rounded-lg border border-slate-700 cursor-pointer">
                        <span class="text-xs font-medium text-slate-200">{{ t.sched_enable }}</span>
                        <input type="checkbox" name="schedule_enabled" {% if settings.schedule_enabled %}checked{% endif %}
                               class="w-4 h-4 accent-emerald-500 cursor-pointer">
                    </label>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div class="bg-slate-900/80 p-3.5 rounded-lg border border-slate-700">
                            <label class="block text-xs text-slate-300 mb-1.5">{{ t.sched_every_days }}</label>
                            <input type="number" name="schedule_every_days" value="{{ settings.schedule_every_days }}" min="1" max="30"
                                   class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono text-center focus:outline-none focus:border-indigo-500">
                        </div>
                        <div class="bg-slate-900/80 p-3.5 rounded-lg border border-slate-700">
                            <label class="block text-xs text-slate-300 mb-1.5">{{ t.sched_at_time }}</label>
                            <input type="time" name="schedule_time" value="{{ settings.schedule_time }}"
                                   class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono text-center focus:outline-none focus:border-indigo-500">
                        </div>
                    </div>

                    <div class="flex justify-between items-center text-xs text-slate-400 bg-slate-900/50 px-3.5 py-2.5 rounded-lg border border-slate-800">
                        <span>{{ t.sched_last_run }}</span>
                        <span id="schedLastRun" class="font-mono text-slate-200">{{ settings.last_scheduled_run or t.never }}</span>
                    </div>

                    <div class="flex flex-wrap justify-between items-center gap-2 pt-1">
                        <button type="button" onclick="triggerSchedulerNow(this)" class="bg-indigo-600/80 hover:bg-indigo-600 text-white px-3.5 py-2 rounded-lg text-xs font-semibold transition">
                            {{ t.sched_run_now }}
                        </button>
                        <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-xs font-semibold transition shadow">
                            💾 {{ t.sched_save }}
                        </button>
                    </div>
                </form>
            </div>

            <!-- Onglet 3 : Utilisateurs (Admin) -->
            {% if user.is_admin %}
            <div id="tab-users" class="hidden space-y-4">
                <form action="/admin/toggle-registration" method="POST" class="flex items-center justify-between bg-slate-900/80 p-3 rounded-lg border border-slate-700">
                    <span class="text-xs text-slate-300">{{ t.allow_reg_label }}</span>
                    <input type="checkbox" name="allow_registration" onchange="this.form.submit()" {% if settings.allow_registration %}checked{% endif %}
                           class="w-4 h-4 accent-emerald-500 cursor-pointer">
                </form>

                <div class="space-y-2 max-h-44 overflow-y-auto pr-1">
                    {% for u in all_users %}
                    <div class="flex justify-between items-center bg-slate-900/90 px-3 py-2 rounded-lg border border-slate-800 text-sm">
                        <div class="flex items-center gap-2">
                            <span class="font-medium text-white">{{ u.username }}</span>
                            <span class="text-[11px] px-2 py-0.5 rounded-full {% if u.is_admin %}bg-indigo-900/70 text-indigo-300 border border-indigo-700{% else %}bg-slate-700 text-slate-300{% endif %}">
                                {{ t.role_admin if u.is_admin else t.role_user }}
                            </span>
                        </div>
                        {% if u.id != user.id %}
                        <form action="/admin/delete-user/{{ u.id }}" method="POST" onsubmit="return confirm('{{ t.confirm_del_user }}');">
                            <button type="submit" class="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-slate-800">🗑️</button>
                        </form>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>

                <form action="/admin/add-user" method="POST" class="space-y-3 pt-3 border-t border-slate-700">
                    <h4 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">{{ t.add_user_section }}</h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <input type="text" name="username" required placeholder="{{ t.user_field }}"
                               class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500">
                        <input type="password" name="password" required placeholder="{{ t.pass_field }}"
                               class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500">
                    </div>
                    <div class="flex justify-between items-center pt-1">
                        <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                            <input type="checkbox" name="is_admin" class="accent-indigo-500">
                            {{ t.role_admin }}
                        </label>
                        <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition">
                            ➕ {{ t.create_user_btn }}
                        </button>
                    </div>
                </form>
            </div>
            {% endif %}

            <!-- Onglet 4 : À propos -->
            <div id="tab-about" class="hidden space-y-4">
                <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 text-center space-y-3">
                    <div class="flex justify-center">
                        """ + LOGO_COMPONENT + """
                    </div>
                    <p class="text-xs text-slate-400">{{ t.about_desc }}</p>
                    <div class="grid grid-cols-2 gap-2 pt-2 text-xs">
                        <div class="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700">
                            <span class="text-slate-400 block">{{ t.about_version }}</span>
                            <span class="font-mono font-bold text-emerald-400 text-sm">v{{ version }}</span>
                        </div>
                        <div class="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700">
                            <span class="text-slate-400 block">{{ t.about_dev }}</span>
                            <span class="font-bold text-indigo-400 text-sm">{{ dev_name }}</span>
                        </div>
                    </div>
                    <div class="pt-3">
                        <a href="{{ github_url }}" target="_blank" class="w-full bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white py-2.5 px-4 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-2">
                            ⭐ {{ t.about_github }}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const COPIED_TEXT = {{ t.copied | tojson }};
        const MODAL_ADD_TITLE = {{ t.modal_add_title | tojson }};
        const MODAL_EDIT_TITLE = {{ t.modal_edit_title | tojson }};
        const GOTIFY_TEST_BTN = {{ t.gotify_test_btn | tojson }};
        const GOTIFY_TESTING = {{ t.gotify_testing | tojson }};
        const GOTIFY_TEST_OK = {{ t.gotify_test_ok | tojson }};
        const GOTIFY_TEST_ERR = {{ t.gotify_test_err | tojson }};
        const TOAST_SYNC_START = {{ t.toast_sync_start | tojson }};
        const TOAST_SYNC_DONE = {{ t.toast_sync_done | tojson }};
        const TOAST_SYNC_ERR = {{ t.toast_sync_err | tojson }};
        const TOAST_SYNC_ALL_START = {{ t.toast_sync_all_start | tojson }};
        const TOAST_SYNC_ALL_DONE = {{ t.toast_sync_all_done | tojson }};
        const NOTIF_EMPTY = {{ t.notif_empty | tojson }};

        function showToast(msg, type = "info") {
            const container = document.getElementById("toastContainer");
            const el = document.createElement("div");
            let colorClass = "bg-indigo-950/95 border-indigo-500 text-indigo-100";
            let icon = "⏳";
            if (type === "success") {
                colorClass = "bg-emerald-900/95 border-emerald-500 text-emerald-100";
                icon = "✅";
            } else if (type === "error") {
                colorClass = "bg-red-900/95 border-red-500 text-red-100";
                icon = "❌";
            }
            el.className = `pointer-events-auto border px-4 py-3 rounded-xl shadow-2xl text-xs font-medium flex items-center gap-2 transition duration-300 ${colorClass}`;
            el.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
            container.appendChild(el);
            setTimeout(() => {
                el.style.opacity = "0";
                setTimeout(() => el.remove(), 300);
            }, 3500);
        }

        function pushNotifToDrawer(message, timeStr) {
            const list = document.getElementById("notifList");
            const badge = document.getElementById("notifBadge");
            if (list.children.length === 1 && list.children[0].classList.contains("text-center")) {
                list.innerHTML = "";
            }
            const item = document.createElement("div");
            item.className = "p-3 text-xs hover:bg-slate-700/40 transition";
            item.innerHTML = `<div class="text-slate-200 font-medium">${message}</div><div class="text-[10px] text-slate-400 mt-1">${timeStr}</div>`;
            list.prepend(item);
            const count = list.children.length;
            badge.innerText = count;
            badge.classList.remove("hidden");
        }

        async function syncSinglePlaylist(btn) {
            const accId = btn.dataset.id;
            const nom = btn.dataset.nom || "Playlist";
            const icon = btn.querySelector(".sync-icon");
            const card = document.getElementById(`card-${accId}`);

            if (icon) icon.classList.add("spinning");
            btn.disabled = true;

            const startMsg = TOAST_SYNC_START.replace("{nom}", nom);
            showToast(startMsg, "info");

            try {
                const res = await fetch(`/api/sync/${accId}`, { method: "POST" });
                const data = await res.json();
                if (data.ok && data.account) {
                    const a = data.account;
                    const badge = document.getElementById(`badge-${accId}`);
                    badge.innerText = a.status_label;
                    badge.className = `px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${a.badge_class}`;

                    document.getElementById(`exp-${accId}`).innerText = a.exp_date_str;
                    const daysEl = document.getElementById(`days-${accId}`);
                    daysEl.innerText = a.days_left_str;
                    daysEl.className = `font-bold ${a.days_class}`;
                    document.getElementById(`cons-${accId}`).innerText = `${a.active_cons} / ${a.max_cons}`;
                    document.getElementById(`sync-${accId}`).innerText = a.last_sync;

                    if (card) {
                        card.classList.add("ring-2", "ring-emerald-500");
                        setTimeout(() => card.classList.remove("ring-2", "ring-emerald-500"), 1200);
                    }

                    const doneMsg = TOAST_SYNC_DONE
                        .replace("{nom}", nom)
                        .replace("{status}", a.status_label)
                        .replace("{cons}", `${a.active_cons}/${a.max_cons}`);
                    showToast(doneMsg, "success");
                    pushNotifToDrawer(doneMsg, a.last_sync);
                } else {
                    showToast(TOAST_SYNC_ERR.replace("{nom}", nom), "error");
                }
            } catch (e) {
                showToast(TOAST_SYNC_ERR.replace("{nom}", nom), "error");
            }

            if (icon) icon.classList.remove("spinning");
            btn.disabled = false;
        }

        async function syncAllPlaylists(btn) {
            const icon = document.getElementById("syncAllIcon");
            if (icon) icon.classList.add("spinning");
            btn.disabled = true;
            showToast(TOAST_SYNC_ALL_START, "info");

            try {
                const res = await fetch("/api/sync-all", { method: "POST" });
                const data = await res.json();
                if (data.ok) {
                    showToast(TOAST_SYNC_ALL_DONE, "success");
                    setTimeout(() => window.location.reload(), 1000);
                }
            } catch (e) {
                if (icon) icon.classList.remove("spinning");
                btn.disabled = false;
            }
        }

        async function triggerSchedulerNow(btn) {
            btn.disabled = true;
            showToast(TOAST_SYNC_ALL_START, "info");
            try {
                const res = await fetch("/api/run-scheduler-now", { method: "POST" });
                const data = await res.json();
                if (data.ok) {
                    showToast(TOAST_SYNC_ALL_DONE, "success");
                    setTimeout(() => window.location.reload(), 1000);
                }
            } catch (e) {
                btn.disabled = false;
            }
        }

        function toggleNotifDrawer() {
            const d = document.getElementById("notifDrawer");
            d.classList.toggle("hidden");
        }

        async function clearNotifications() {
            await fetch("/api/notifications/clear", { method: "POST" });
            document.getElementById("notifList").innerHTML = `<div class="p-6 text-center text-xs text-slate-400">${NOTIF_EMPTY}</div>`;
            document.getElementById("notifBadge").classList.add("hidden");
        }

        function fallbackCopyText(text) {
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.top = "-9999px";
            ta.style.left = "-9999px";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            try { document.execCommand("copy"); } catch (e) {}
            document.body.removeChild(ta);
        }

        function copyFromAttr(btn) {
            const text = btn.getAttribute("data-copy") || "";
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).catch(() => fallbackCopyText(text));
            } else {
                fallbackCopyText(text);
            }

            if (!btn.dataset.origText) {
                btn.dataset.origText = btn.innerText;
            }
            btn.innerText = COPIED_TEXT;
            btn.classList.remove("bg-slate-700", "hover:bg-slate-600", "text-slate-200");
            btn.classList.add("bg-emerald-600", "hover:bg-emerald-500", "text-white", "font-semibold");

            if (btn.copyTimeout) clearTimeout(btn.copyTimeout);
            btn.copyTimeout = setTimeout(() => {
                btn.innerText = btn.dataset.origText;
                btn.classList.remove("bg-emerald-600", "hover:bg-emerald-500", "text-white", "font-semibold");
                btn.classList.add("bg-slate-700", "hover:bg-slate-600", "text-slate-200");
            }, 1600);
        }

        async function testGotify() {
            const btn = document.getElementById('gotify_test_btn');
            const url = document.getElementById('field_gotify_url').value.trim();
            const token = document.getElementById('field_gotify_token').value.trim();
            const nom = document.getElementById('field_nom').value.trim() || 'IPTV';
            const days = document.getElementById('field_gotify_days').value.trim() || '30';
            const custom_msg = document.getElementById('field_gotify_custom_msg').value.trim();

            btn.innerText = GOTIFY_TESTING;
            btn.disabled = true;

            try {
                const res = await fetch('/test-gotify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, token, nom, days, custom_msg })
                });
                const data = await res.json();
                if (data.ok) {
                    btn.innerText = GOTIFY_TEST_OK;
                    btn.classList.remove('bg-indigo-600/80', 'hover:bg-indigo-600', 'bg-red-600');
                    btn.classList.add('bg-emerald-600');
                } else {
                    btn.innerText = GOTIFY_TEST_ERR;
                    btn.classList.remove('bg-indigo-600/80', 'hover:bg-indigo-600', 'bg-emerald-600');
                    btn.classList.add('bg-red-600');
                }
            } catch (e) {
                btn.innerText = GOTIFY_TEST_ERR;
                btn.classList.remove('bg-indigo-600/80', 'hover:bg-indigo-600', 'bg-emerald-600');
                btn.classList.add('bg-red-600');
            }

            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = GOTIFY_TEST_BTN;
                btn.classList.remove('bg-emerald-600', 'bg-red-600');
                btn.classList.add('bg-indigo-600/80', 'hover:bg-indigo-600');
            }, 3000);
        }

        const modal = document.getElementById('accountModal');
        const settingsModal = document.getElementById('settingsModal');
        const gotifyFields = document.getElementById('gotify_fields');

        function toggleGotifyFields(enabled) {
            if (enabled) gotifyFields.classList.remove('hidden');
            else gotifyFields.classList.add('hidden');
        }

        function openAddModal() {
            document.getElementById('modalTitle').innerText = MODAL_ADD_TITLE;
            document.getElementById('field_id').value = '';
            document.getElementById('field_nom').value = '';
            document.getElementById('field_m3u_paste').value = '';
            document.getElementById('field_host').value = '';
            document.getElementById('field_username').value = '';
            document.getElementById('field_password').value = '';
            document.getElementById('field_gotify_enabled').checked = false;
            document.getElementById('field_gotify_url').value = '';
            document.getElementById('field_gotify_token').value = '';
            document.getElementById('field_gotify_days').value = '30';
            document.getElementById('field_gotify_freq').value = '3';
            document.getElementById('field_gotify_custom_msg').value = '';
            toggleGotifyFields(false);
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }

        function openEditModal(acc) {
            document.getElementById('modalTitle').innerText = MODAL_EDIT_TITLE;
            document.getElementById('field_id').value = acc.id;
            document.getElementById('field_nom').value = acc.nom;
            document.getElementById('field_m3u_paste').value = '';
            document.getElementById('field_host').value = acc.host;
            document.getElementById('field_username').value = acc.username;
            document.getElementById('field_password').value = acc.password;

            const gotifyEnabled = acc.gotify_enabled || false;
            document.getElementById('field_gotify_enabled').checked = gotifyEnabled;
            document.getElementById('field_gotify_url').value = acc.gotify_url || '';
            document.getElementById('field_gotify_token').value = acc.gotify_token || '';
            document.getElementById('field_gotify_days').value = acc.gotify_days || 30;
            document.getElementById('field_gotify_freq').value = acc.gotify_freq || 3;
            document.getElementById('field_gotify_custom_msg').value = acc.gotify_custom_msg || '';
            toggleGotifyFields(gotifyEnabled);

            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }

        function closeModal() {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }

        function openSettingsModal(defaultTab = 'general') {
            settingsModal.classList.remove('hidden');
            settingsModal.classList.add('flex');
            switchSettingsTab(defaultTab);
        }

        function closeSettingsModal() {
            settingsModal.classList.add('hidden');
            settingsModal.classList.remove('flex');
        }

        function switchSettingsTab(tabName) {
            ['general', 'scheduler', 'users', 'about'].forEach(name => {
                const content = document.getElementById(`tab-${name}`);
                const btn = document.getElementById(`tabbtn-${name}`);
                if (content) {
                    if (name === tabName) content.classList.remove('hidden');
                    else content.classList.add('hidden');
                }
                if (btn) {
                    if (name === tabName) {
                        btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition";
                    } else {
                        btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-slate-300 hover:bg-slate-700 transition";
                    }
                }
            });
        }

        function parseM3uUrl(urlStr) {
            try {
                const url = new URL(urlStr.trim());
                const host = url.protocol + '//' + url.host;
                const username = url.searchParams.get('username');
                const password = url.searchParams.get('password');

                if (host) document.getElementById('field_host').value = host;
                if (username) document.getElementById('field_username').value = username;
                if (password) document.getElementById('field_password').value = password;
            } catch (e) {}
        }
    </script>
</body>
</html>
"""

@app.route("/favicon.svg")
@app.route("/favicon.ico")
def serve_favicon():
    return Response(FAVICON_SVG, mimetype="image/svg+xml")

@app.route("/logo")
def serve_logo():
    for fname in ["logo.jpg", "logo.png", "m3u-monitor2.jpg"]:
        p = os.path.join(DATA_DIR, fname)
        if os.path.exists(p):
            return send_file(p)
        p_app = os.path.join("/app", fname)
        if os.path.exists(p_app):
            return send_file(p_app)
    return "", 404

@app.route("/set-lang", methods=["POST"])
def set_lang():
    lang = request.form.get("lang", "fr")
    if lang in TRANSLATIONS:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))

@app.route("/settings/scheduler", methods=["POST"])
@login_required
def save_scheduler_settings():
    settings = load_settings()
    settings["schedule_enabled"] = "schedule_enabled" in request.form
    try:
        settings["schedule_every_days"] = max(1, int(request.form.get("schedule_every_days", 1)))
    except ValueError:
        settings["schedule_every_days"] = 1
    sched_time = request.form.get("schedule_time", "02:00").strip()
    settings["schedule_time"] = sched_time if sched_time else "02:00"
    save_settings(settings)
    return redirect(url_for("index"))

@app.route("/api/sync/<acc_id>", methods=["POST"])
@login_required
def api_sync_single(acc_id):
    user = get_current_user()
    lang = get_lang()
    t = TRANSLATIONS[lang]
    all_accs = load_all_accounts()
    target = None
    for a in all_accs:
        if a.get("id") == acc_id and a.get("owner_id") == user["id"]:
            target = a
            break
    if not target:
        return jsonify({"ok": False}), 404

    view = build_account_view(target, t, force_refresh=True)
    msg = t["toast_sync_done"].format(
        nom=view["nom"],
        status=view["status_label"],
        cons=f"{view['active_cons']}/{view['max_cons']}"
    )
    add_notification(user["id"], msg, "success")
    return jsonify({"ok": True, "account": view})

@app.route("/api/sync-all", methods=["POST"])
@login_required
def api_sync_all():
    user = get_current_user()
    lang = get_lang()
    t = TRANSLATIONS[lang]
    all_accs = load_all_accounts()
    user_accs = [a for a in all_accs if a.get("owner_id") == user["id"]]
    for acc in user_accs:
        view = build_account_view(acc, t, force_refresh=True)
        msg = t["toast_sync_done"].format(
            nom=view["nom"],
            status=view["status_label"],
            cons=f"{view['active_cons']}/{view['max_cons']}"
        )
        add_notification(user["id"], msg, "success")
    return jsonify({"ok": True})

@app.route("/api/run-scheduler-now", methods=["POST"])
@login_required
def api_run_scheduler_now():
    lang = get_lang()
    execute_scheduled_sync_job(lang)
    return jsonify({"ok": True})

@app.route("/api/notifications/clear", methods=["POST"])
@login_required
def api_clear_notifications():
    user = get_current_user()
    clear_user_notifications(user["id"])
    return jsonify({"ok": True})

@app.route("/test-gotify", methods=["POST"])
@login_required
def test_gotify_route():
    lang = get_lang()
    t = TRANSLATIONS[lang]
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    token = data.get("token", "").strip()
    nom = data.get("nom", "IPTV").strip() or "IPTV"
    days = data.get("days", "30")
    custom_msg = data.get("custom_msg", "").strip()

    date_sample = datetime.now().strftime("%d/%m/%Y")
    title = t["gotify_test_title"].format(nom=nom)
    if custom_msg:
        message = format_gotify_message(custom_msg, t["gotify_test_body"], nom, days, date_sample)
    else:
        message = t["gotify_test_body"].format(nom=nom)

    ok = send_gotify_alert(url, token, title, message)
    return jsonify({"ok": ok})

@app.route("/setup", methods=["GET", "POST"])
def setup():
    users = load_users()
    if users:
        return redirect(url_for("login"))

    lang = get_lang()
    t = TRANSLATIONS[lang]

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username and password:
            admin_id = str(uuid.uuid4())
            new_admin = {
                "id": admin_id,
                "username": username,
                "password_hash": generate_password_hash(password),
                "is_admin": True
            }
            save_users([new_admin])
            load_all_accounts(default_owner_id=admin_id)
            session["user_id"] = admin_id
            session.permanent = True
            return redirect(url_for("index"))

    return render_template_string(
        AUTH_TEMPLATE,
        lang=lang,
        t=t,
        flags=FLAGS_SVG,
        version=APP_VERSION,
        dev_name=DEV_NAME,
        title=t["setup_title"],
        subtitle=t["setup_sub"],
        btn_label=t["setup_btn"],
        mode="setup",
        allow_registration=False
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    users = load_users()
    if not users:
        return redirect(url_for("setup"))
    if get_current_user():
        return redirect(url_for("index"))

    lang = get_lang()
    t = TRANSLATIONS[lang]
    settings = load_settings()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        for u in users:
            if u.get("username", "").lower() == username.lower() and check_password_hash(u.get("password_hash", ""), password):
                session.clear()
                session["user_id"] = u["id"]
                session.permanent = True
                return redirect(url_for("index"))
        flash(t["err_invalid_login"])

    return render_template_string(
        AUTH_TEMPLATE,
        lang=lang,
        t=t,
        flags=FLAGS_SVG,
        version=APP_VERSION,
        dev_name=DEV_NAME,
        title=t["login_title"],
        subtitle=t["login_sub"],
        btn_label=t["login_btn"],
        mode="login",
        allow_registration=settings.get("allow_registration", True)
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    users = load_users()
    if not users:
        return redirect(url_for("setup"))

    lang = get_lang()
    t = TRANSLATIONS[lang]
    settings = load_settings()

    if not settings.get("allow_registration", True):
        flash(t["err_reg_disabled"])
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if any(u.get("username", "").lower() == username.lower() for u in users):
            flash(t["err_user_exists"])
        elif username and password:
            new_uid = str(uuid.uuid4())
            users.append({
                "id": new_uid,
                "username": username,
                "password_hash": generate_password_hash(password),
                "is_admin": False
            })
            save_users(users)
            session.clear()
            session["user_id"] = new_uid
            session.permanent = True
            return redirect(url_for("index"))

    return render_template_string(
        AUTH_TEMPLATE,
        lang=lang,
        t=t,
        flags=FLAGS_SVG,
        version=APP_VERSION,
        dev_name=DEV_NAME,
        title=t["register_title"],
        subtitle=t["register_sub"],
        btn_label=t["register_btn"],
        mode="register",
        allow_registration=True
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    user = get_current_user()
    lang = get_lang()
    t = TRANSLATIONS[lang]
    settings = load_settings()

    all_accounts = load_all_accounts(default_owner_id=user["id"])
    user_accounts = [a for a in all_accounts if a.get("owner_id") == user["id"]]

    with ThreadPoolExecutor(max_workers=10) as executor:
        accounts = list(executor.map(lambda acc: build_account_view(acc, t, force_refresh=False), user_accounts))

    notifications = load_notifications(user["id"])

    return render_template_string(
        DASHBOARD_TEMPLATE,
        accounts=accounts,
        user=user,
        all_users=load_users() if user.get("is_admin") else [],
        settings=settings,
        notifications=notifications,
        flags=FLAGS_SVG,
        version=APP_VERSION,
        dev_name=DEV_NAME,
        github_url=GITHUB_URL,
        lang=lang,
        t=t
    )

@app.route("/save", methods=["POST"])
@login_required
def save_account_route():
    user = get_current_user()
    acc_id = request.form.get("id", "").strip()
    nom = request.form.get("nom", "").strip()
    host = request.form.get("host", "").strip().rstrip("/")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    gotify_enabled = "gotify_enabled" in request.form
    gotify_url = request.form.get("gotify_url", "").strip()
    gotify_token = request.form.get("gotify_token", "").strip()
    gotify_custom_msg = request.form.get("gotify_custom_msg", "").strip()
    try:
        gotify_days = int(request.form.get("gotify_days", 30))
    except ValueError:
        gotify_days = 30
    try:
        gotify_freq = int(request.form.get("gotify_freq", 3))
    except ValueError:
        gotify_freq = 3

    if not (nom and host and username and password):
        return redirect(url_for("index"))

    accounts = load_all_accounts()
    enc_password = encrypt_str(password)
    target_acc = None

    if acc_id:
        for item in accounts:
            if item.get("id") == acc_id and item.get("owner_id") == user["id"]:
                item["nom"] = nom
                item["host"] = host
                item["username"] = username
                item["password"] = enc_password
                item["gotify_enabled"] = gotify_enabled
                item["gotify_url"] = gotify_url
                item["gotify_token"] = gotify_token
                item["gotify_days"] = gotify_days
                item["gotify_freq"] = gotify_freq
                item["gotify_custom_msg"] = gotify_custom_msg
                target_acc = item
                break
    else:
        target_acc = {
            "id": str(uuid.uuid4()),
            "owner_id": user["id"],
            "nom": nom,
            "host": host,
            "username": username,
            "password": enc_password,
            "gotify_enabled": gotify_enabled,
            "gotify_url": gotify_url,
            "gotify_token": gotify_token,
            "gotify_days": gotify_days,
            "gotify_freq": gotify_freq,
            "gotify_custom_msg": gotify_custom_msg,
            "last_gotify_date": None,
            "last_sync": None,
            "cached_info": None
        }
        accounts.append(target_acc)

    save_all_accounts(accounts)
    if target_acc:
        fetch_live_xtream_info(target_acc)
    return redirect(url_for("index"))

@app.route("/delete/<acc_id>", methods=["POST"])
@login_required
def delete_account_route(acc_id):
    user = get_current_user()
    accounts = load_all_accounts()
    accounts = [a for a in accounts if not (a.get("id") == acc_id and a.get("owner_id") == user["id"])]
    save_all_accounts(accounts)
    return redirect(url_for("index"))

@app.route("/admin/toggle-registration", methods=["POST"])
@login_required
def toggle_registration():
    user = get_current_user()
    if user.get("is_admin"):
        settings = load_settings()
        settings["allow_registration"] = "allow_registration" in request.form
        save_settings(settings)
    return redirect(url_for("index"))

@app.route("/admin/add-user", methods=["POST"])
@login_required
def admin_add_user():
    user = get_current_user()
    if user.get("is_admin"):
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = "is_admin" in request.form
        users = load_users()
        if username and password and not any(u.get("username", "").lower() == username.lower() for u in users):
            users.append({
                "id": str(uuid.uuid4()),
                "username": username,
                "password_hash": generate_password_hash(password),
                "is_admin": is_admin
            })
            save_users(users)
    return redirect(url_for("index"))

@app.route("/admin/delete-user/<target_id>", methods=["POST"])
@login_required
def admin_delete_user(target_id):
    user = get_current_user()
    if user.get("is_admin") and target_id != user["id"]:
        users = [u for u in load_users() if u.get("id") != target_id]
        save_users(users)
        accounts = [a for a in load_all_accounts() if a.get("owner_id") != target_id]
        save_all_accounts(accounts)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
