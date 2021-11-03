#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


"""
CLI for running a Private Lift study


Usage:
    pc-cli create_instance <instance_id> --config=<config_file> --role=<pl_role> --game_type=<game_type> --input_path=<input_path> --output_dir=<output_dir> --num_pid_containers=<num_pid_containers> --num_mpc_containers=<num_mpc_containers> [--attribution_rule=<attribution_rule> --aggregation_type=<aggregation_type> --concurrency=<concurrency> --num_files_per_mpc_container=<num_files_per_mpc_container> --padding_size=<padding_size> --k_anonymity_threshold=<k_anonymity_threshold> --hmac_key=<base64_key> --fail_fast] [options]
    pc-cli id_match <instance_id> --config=<config_file> [--server_ips=<server_ips> --dry_run] [options]
    pc-cli prepare_compute_input <instance_id> --config=<config_file> [--dry_run --log_cost_to_s3] [options]
    pc-cli compute_metrics <instance_id> --config=<config_file> [--server_ips=<server_ips> --dry_run --log_cost_to_s3] [options]
    pc-cli aggregate_shards <instance_id> --config=<config_file> [--server_ips=<server_ips> --dry_run --log_cost_to_s3] [options]
    pc-cli validate <instance_id> --config=<config_file> --aggregated_result_path=<aggregated_result_path> --expected_result_path=<expected_result_path> [options]
    pc-cli run_post_processing_handlers <instance_id> --config=<config_file> [--aggregated_result_path=<aggregated_result_path> --dry_run] [options]
    pc-cli run_next <instance_id> --config=<config_file> [--server_ips=<server_ips>] [options]
    pc-cli get_instance <instance_id> --config=<config_file> [options]
    pc-cli get_server_ips <instance_id> --config=<config_file> [options]
    pc-cli get_pid <instance_id> --config=<config_file> [options]
    pc-cli get_mpc <instance_id> --config=<config_file> [options]
    pc-cli run_instance <instance_id> --config=<config_file> --input_path=<input_path> --num_shards=<num_shards> [--tries_per_stage=<tries_per_stage> --dry_run --legacy] [options]
    pc-cli run_instances <instance_ids> --config=<config_file> --input_paths=<input_paths> --num_shards_list=<num_shards_list> [--tries_per_stage=<tries_per_stage> --dry_run --legacy] [options]
    pc-cli run_study <study_id> --config=<config_file> --objective_ids=<objective_ids> --input_paths=<input_paths> [--tries_per_stage=<tries_per_stage> --dry_run --legacy] [options]
    pc-cli cancel_current_stage <instance_id> --config=<config_file> [options]
    pc-cli print_instance <instance_id> --config=<config_file> [options]

Options:
    -h --help                Show this help
    --log_path=<path>        Override the default path where logs are saved
    --verbose                Set logging level to DEBUG
"""

import logging
import os
from pathlib import Path, PurePath

import schema
from docopt import docopt
from fbpcp.util import yaml
from fbpcs.pl_coordinator.pl_instance_runner import run_instance, run_instances
from fbpcs.pl_coordinator.pl_study_runner import run_study
from fbpcs.private_computation.entity.private_computation_instance import (
    AggregationType,
    AttributionRule,
    PrivateComputationRole,
    PrivateComputationGameType,
)
from fbpcs.private_computation.entity.private_computation_legacy_stage_flow import (
    PrivateComputationLegacyStageFlow,
)
from fbpcs.private_computation_cli.private_computation_service_wrapper import (
    aggregate_shards,
    cancel_current_stage,
    compute_metrics,
    create_instance,
    get_instance,
    get_mpc,
    get_pid,
    get_server_ips,
    id_match,
    prepare_compute_input,
    print_instance,
    run_next,
    run_post_processing_handlers,
    validate,
)
from fbpcs.utils.config_yaml.config_yaml_dict import ConfigYamlDict


def main():
    s = schema.Schema(
        {
            "create_instance": bool,
            "id_match": bool,
            "prepare_compute_input": bool,
            "compute_metrics": bool,
            "aggregate_shards": bool,
            "validate": bool,
            "run_post_processing_handlers": bool,
            "run_next": bool,
            "get_instance": bool,
            "get_server_ips": bool,
            "get_pid": bool,
            "get_mpc": bool,
            "run_instance": bool,
            "run_instances": bool,
            "run_study": bool,
            "cancel_current_stage": bool,
            "print_instance": bool,
            "<instance_id>": schema.Or(None, str),
            "<instance_ids>": schema.Or(None, schema.Use(lambda arg: arg.split(","))),
            "<study_id>": schema.Or(None, str),
            "--config": schema.And(schema.Use(PurePath), os.path.exists),
            "--role": schema.Or(
                None,
                schema.And(
                    schema.Use(str.upper),
                    lambda s: s in ("PUBLISHER", "PARTNER"),
                    schema.Use(PrivateComputationRole),
                ),
            ),
            "--game_type": schema.Or(
                None,
                schema.And(
                    schema.Use(str.upper),
                    lambda s: s in ("LIFT", "ATTRIBUTION"),
                    schema.Use(PrivateComputationGameType),
                ),
            ),
            "--objective_ids": schema.Or(None, schema.Use(lambda arg: arg.split(","))),
            "--input_path": schema.Or(None, str),
            "--input_paths": schema.Or(None, schema.Use(lambda arg: arg.split(","))),
            "--output_dir": schema.Or(None, str),
            "--aggregated_result_path": schema.Or(None, str),
            "--expected_result_path": schema.Or(None, str),
            "--num_pid_containers": schema.Or(None, schema.Use(int)),
            "--num_mpc_containers": schema.Or(None, schema.Use(int)),
            "--aggregation_type": schema.Or(None, schema.Use(AggregationType)),
            "--attribution_rule": schema.Or(None, schema.Use(AttributionRule)),
            "--num_files_per_mpc_container": schema.Or(None, schema.Use(int)),
            "--num_shards": schema.Or(None, schema.Use(int)),
            "--num_shards_list": schema.Or(
                None, schema.Use(lambda arg: arg.split(","))
            ),
            "--server_ips": schema.Or(None, schema.Use(lambda arg: arg.split(","))),
            "--concurrency": schema.Or(None, schema.Use(int)),
            "--padding_size": schema.Or(None, schema.Use(int)),
            "--k_anonymity_threshold": schema.Or(None, schema.Use(int)),
            "--hmac_key": schema.Or(None, str),
            "--tries_per_stage": schema.Or(None, schema.Use(int)),
            "--fail_fast": bool,
            "--legacy": bool,
            "--dry_run": bool,
            "--log_path": schema.Or(None, schema.Use(Path)),
            "--log_cost_to_s3": schema.Or(None, schema.Use(bool)),
            "--verbose": bool,
            "--help": bool,
        }
    )

    arguments = s.validate(docopt(__doc__))
    config = ConfigYamlDict.from_dict(yaml.load(Path(arguments["--config"])))

    log_path = arguments["--log_path"]
    log_level = logging.DEBUG if arguments["--verbose"] else logging.INFO
    instance_id = arguments["<instance_id>"]

    logging.basicConfig(filename=log_path, level=log_level)
    logger = logging.getLogger(__name__)

    if arguments["create_instance"]:
        logger.info(f"Create instance: {instance_id}")

        create_instance(
            config=config,
            instance_id=instance_id,
            role=arguments["--role"],
            game_type=arguments["--game_type"],
            logger=logger,
            input_path=arguments["--input_path"],
            output_dir=arguments["--output_dir"],
            num_pid_containers=arguments["--num_pid_containers"],
            num_mpc_containers=arguments["--num_mpc_containers"],
            attribution_rule=arguments["--attribution_rule"],
            aggregation_type=arguments["--aggregation_type"],
            concurrency=arguments["--concurrency"],
            num_files_per_mpc_container=arguments["--num_files_per_mpc_container"],
            hmac_key=arguments["--hmac_key"],
            padding_size=arguments["--padding_size"],
            k_anonymity_threshold=arguments["--k_anonymity_threshold"],
            fail_fast=arguments["--fail_fast"],
        )
    elif arguments["id_match"]:
        logger.info(f"Run id match on instance: {instance_id}")
        id_match(
            config=config,
            instance_id=instance_id,
            logger=logger,
            server_ips=arguments["--server_ips"],
            dry_run=arguments["--dry_run"],
        )
    elif arguments["prepare_compute_input"]:
        logger.info(f"Prepare compute input for instance: {instance_id}")
        prepare_compute_input(
            config=config,
            instance_id=instance_id,
            logger=logger,
            dry_run=arguments["--dry_run"],
            log_cost_to_s3=arguments["--log_cost_to_s3"],
        )
    elif arguments["compute_metrics"]:
        logger.info(f"Compute instance: {instance_id}")
        compute_metrics(
            config=config,
            instance_id=instance_id,
            logger=logger,
            server_ips=arguments["--server_ips"],
            dry_run=arguments["--dry_run"],
            log_cost_to_s3=arguments["--log_cost_to_s3"],
        )
    elif arguments["run_post_processing_handlers"]:
        logger.info(f"post processing handlers instance: {instance_id}")
        run_post_processing_handlers(
            config=config,
            instance_id=instance_id,
            logger=logger,
            aggregated_result_path=arguments["--aggregated_result_path"],
            dry_run=arguments["--dry_run"],
        )
    elif arguments["run_next"]:
        logger.info(f"run_next instance: {instance_id}")
        run_next(
            config=config,
            instance_id=instance_id,
            logger=logger,
            server_ips=arguments["--server_ips"],
        )
    elif arguments["get_instance"]:
        logger.info(f"Get instance: {instance_id}")
        get_instance(config, instance_id, logger)
    elif arguments["get_server_ips"]:
        get_server_ips(config, instance_id, logger)
    elif arguments["get_pid"]:
        logger.info(f"Get PID instance: {instance_id}")
        get_pid(config, instance_id, logger)
    elif arguments["get_mpc"]:
        logger.info(f"Get MPC instance: {instance_id}")
        get_mpc(config, instance_id, logger)
    elif arguments["aggregate_shards"]:
        logger.info(f"Aggregate instance: {instance_id}")
        aggregate_shards(
            config=config,
            instance_id=instance_id,
            logger=logger,
            server_ips=arguments["--server_ips"],
            dry_run=arguments["--dry_run"],
            log_cost_to_s3=arguments["--log_cost_to_s3"],
        )
    elif arguments["validate"]:
        logger.info(f"Vallidate instance: {instance_id}")
        validate(
            config=config,
            instance_id=instance_id,
            aggregated_result_path=arguments["--aggregated_result_path"],
            expected_result_path=arguments["--expected_result_path"],
            logger=logger,
        )
    elif arguments["run_instance"]:
        if arguments["--legacy"]:
            stage_flow = PrivateComputationLegacyStageFlow
        else:
            # I will replace this in later diffs in stack
            stage_flow = PrivateComputationLegacyStageFlow

        logger.info(f"Running instance: {instance_id}")
        run_instance(
            config=config,
            instance_id=instance_id,
            input_path=arguments["--input_path"],
            num_shards=["--num_shards"],
            stage_flow=stage_flow,
            logger=logger,
            num_tries=arguments["--tries_per_stage"],
            dry_run=arguments["--dry_run"],
        )
    elif arguments["run_instances"]:
        if arguments["--legacy"]:
            stage_flow = PrivateComputationLegacyStageFlow
        else:
            # I will replace this in later diffs in stack
            stage_flow = PrivateComputationLegacyStageFlow
        run_instances(
            config=config,
            instance_ids=arguments["<instance_ids>"],
            input_paths=arguments["--input_paths"],
            num_shards_list=arguments["--num_shards_list"],
            stage_flow=stage_flow,
            logger=logger,
            num_tries=arguments["--tries_per_stage"],
            dry_run=arguments["--dry_run"],
        )
    elif arguments["run_study"]:
        if arguments["--legacy"]:
            stage_flow = PrivateComputationLegacyStageFlow
        else:
            # I will replace this in later diffs in stack
            stage_flow = PrivateComputationLegacyStageFlow
        run_study(
            config=config,
            study_id=arguments["<study_id>"],
            objective_ids=arguments["--objective_ids"],
            input_paths=arguments["--input_paths"],
            logger=logger,
            stage_flow=stage_flow,
            num_tries=arguments["--tries_per_stage"],
            dry_run=arguments["--dry_run"],
        )
    elif arguments["cancel_current_stage"]:
        logger.info(f"Canceling the current running stage of instance: {instance_id}")
        cancel_current_stage(
            config=config,
            instance_id=instance_id,
            logger=logger,
        )
    elif arguments["print_instance"]:
        print_instance(
            config=config,
            instance_id=instance_id,
            logger=logger,
        )


if __name__ == "__main__":
    main()