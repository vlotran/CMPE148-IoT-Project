#!/bin/bash

# Run all CoAP experiments with 3 repetitions each.
# Failed runs are logged to coap_failed_runs.log.
# Full terminal output is saved to coap_experiment_output.log.

set +e

LOG_FILE="coap_experiment_output.log"
FAIL_FILE="coap_failed_runs.log"

echo "Starting CoAP experiments..." | tee "$LOG_FILE"
echo "" > "$FAIL_FILE"

run_exp () {
    RUN_ID="$1"
    shift

    echo "========================================" | tee -a "$LOG_FILE"
    echo "Running: $RUN_ID" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"

    sudo python3 src/run_experiment.py "$@" --run_id "$RUN_ID" >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        echo "FAILED: $RUN_ID" | tee -a "$FAIL_FILE"
    else
        echo "SUCCESS: $RUN_ID" | tee -a "$LOG_FILE"
    fi
}

# Refresh sudo timestamp before long run
sudo -v

# # -----------------------------
# # 1. Baseline
# # -----------------------------
# for rep in 1 2 3; do
#     run_exp "coap_baseline_$rep" --protocol coap --duration 60 --sensors 2 --delay 5ms --bw_sensor 10 --bw_gateway 100
# done

# # -----------------------------
# # 2. Scalability
# # -----------------------------
# for sensors in 1 2 5 10; do
#     for rep in 1 2 3; do
#         run_exp "coap_s${sensors}_rep${rep}" --protocol coap --duration 60 --sensors "$sensors" --delay 5ms --bw_sensor 10 --bw_gateway 100
#     done
# done

# # -----------------------------
# # 3. Delay sensitivity
# # -----------------------------
# for delay in 1ms 10ms 25ms 50ms 100ms; do
#     delay_id=${delay/ms/}
#     for rep in 1 2 3; do
#         run_exp "coap_delay${delay_id}_rep${rep}" --protocol coap --duration 60 --sensors 5 --delay "$delay" --bw_sensor 10 --bw_gateway 100
#     done
# done

# # -----------------------------
# # 4. Bandwidth sensitivity
# # -----------------------------
# for bw in 0.5 1 2 5 10; do
#     bw_id=${bw/./_}
#     for rep in 1 2 3; do
#         run_exp "coap_bw${bw_id}_rep${rep}" --protocol coap --duration 60 --sensors 5 --delay 5ms --bw_sensor "$bw" --bw_gateway 100
#     done
# done

# echo "========================================" | tee -a "$LOG_FILE"
# echo "CoAP experiments complete." | tee -a "$LOG_FILE"
# echo "Check failures with: cat $FAIL_FILE" | tee -a "$LOG_FILE"
# -----------------------------
# 5. Reliability under packet loss
# -----------------------------
for loss in 0 1 3 5 10; do
    loss_id=${loss/./_}
    for rep in 1 2 3; do
        run_exp "mqtt_loss${loss_id}_rep${rep}" \
            --protocol mqtt \
            --duration 60 \
            --sensors 5 \
            --delay 5 \
            --bw_sensor 10 \
            --bw_gateway 100 \
            --loss "$loss"
    done
done

for loss in 0 1 3 5 10; do
    loss_id=${loss/./_}
    for rep in 1 2 3; do
        run_exp "coap_loss${loss_id}_rep${rep}" \
            --protocol coap \
            --duration 60 \
            --sensors 5 \
            --delay 5 \
            --bw_sensor 10 \
            --bw_gateway 100 \
            --loss "$loss"
    done
done