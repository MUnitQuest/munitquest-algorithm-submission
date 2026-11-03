cat <<'EOF'

╔══════════════════════════════════════════════════════════════╗
║                 ⚙ Last-Minute Maintenance ⚙                  ║
╠══════════════════════════════════════════════════════════════╣
║ Our scoring system is currently undergoing some              ║
║ last-minute maintenance and updates.                         ║
║                                                              ║
║ Please forgive any inconvenience and thank you for your      ║
║ patience while things are being polished to get started.     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

EOF

echo "Writing placeholder scores.json..."
echo '{"score": 0.0, "f1_mean": 0.0}' > /app/output/scores.json