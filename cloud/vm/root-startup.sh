#! /bin/bash
# Make a note of when we were triggered - if it was early morning we know it was an automated start
start_time=$(date +"%H:%M")

now=$(date +"%Y%m%d-%H%M")

# If we were triggered at ridiculous o'clock, shutdown now as it was an automated start
if [[ "${start_time}" > "01:00" ]] && [[ "${start_time}" < "05:00" ]]; then
 echo "Automated run"

 echo "Running /home/runner/runner-startup.sh, logging to /home/runner/startup-${now}.log"
 sudo -u runner bash -c "source /home/runner/.bashrc && /home/runner/runner-startup.sh /home/runner/logs/startup-${now}.log"

 echo "Shutting down now"
 sudo -u runner bash -c "echo 'Automated run - shutting down now' >> /home/runner/logs/startup-${now}.log"
 poweroff
else
 echo "Human-triggered run; not auto-running R, but leaving VM running"
 sudo -u runner bash -c "echo 'Human-triggered run; not auto-running R, but leaving VM running' > /home/runner/logs/startup-${now}.log"
fi

echo "End of startup script"
