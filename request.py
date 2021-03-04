#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta
import pathlib
import sys

from yapapi import (
    Executor,
    NoPaymentAccountError,
    Task,
    __version__ as yapapi_version,
    WorkContext,
    windows_event_loop_fix,
)
from yapapi.log import enable_default_logger, log_summary, log_event_repr  # noqa
from yapapi.package import vm
from yapapi.rest.activity import BatchTimeoutError

examples_dir = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(examples_dir))

from utils import (
    build_parser,
    TEXT_COLOR_CYAN,
    TEXT_COLOR_DEFAULT,
    TEXT_COLOR_RED,
    TEXT_COLOR_YELLOW,
)


async def main(subnet_tag, driver=None, network=None):
    package = await vm.repo(
        image_hash="16497439b1f4c31e39b76dc12b68a45e530e59fafdf73ed2ed92fc7e",
        min_mem_gib=4,
        min_storage_gib=2.0,
    )

    async def worker(ctx: WorkContext, tasks):
        script_dir = pathlib.Path(__file__).resolve().parent
        async for task in tasks:
            frame = task.data
            ctx.run("/bin/sh", "-c", "./generate_data.sh")
            output_file = f"output/{frame}.zip"
            ctx.download_file(f"/golem/output/data.zip", output_file)
            try:
                # Set timeout for executing the script on the provider. Two minutes is plenty
                # of time for computing a single frame, for other tasks it may be not enough.
                # If the timeout is exceeded, this worker instance will be shut down and all
                # remaining tasks, including the current one, will be computed by other providers.
                yield ctx.commit(timeout=timedelta(seconds=1750))
                # TODO: Check if job results are valid
                # and reject by: task.reject_task(reason = 'invalid file')
                task.accept_result(result=output_file)
            except BatchTimeoutError:
                print(
                    f"{TEXT_COLOR_RED}"
                    f"Task {task} timed out on {ctx.provider_name}, time: {task.running_time}"
                    f"{TEXT_COLOR_DEFAULT}"
                )
                raise

    # Iterator over the frame indices that we want to render
    frames: range = range(0, 60, )
    # Worst-case overhead, in minutes, for initialization (negotiation, file transfer etc.)
    # TODO: make this dynamic, e.g. depending on the size of files to transfer
    init_overhead = 3
    # Providers will not accept work if the timeout is outside of the [5 min, 30min] range.
    # We increase the lower bound to 6 min to account for the time needed for our demand to
    # reach the providers.
    min_timeout, max_timeout = 6, 30

    timeout = timedelta(minutes=max(min(init_overhead + len(frames) * 2, max_timeout), min_timeout))

    # By passing `event_consumer=log_summary()` we enable summary logging.
    # See the documentation of the `yapapi.log` module on how to set
    # the level of detail and format of the logged information.
    async with Executor(
        package=package,
        max_workers=30,
        budget=10.0,
        timeout=timeout,
        subnet_tag=subnet_tag,
        driver=driver,
        network=network,
        event_consumer=log_summary(log_event_repr),
    ) as executor:

        sys.stderr.write(
            f"yapapi version: {TEXT_COLOR_YELLOW}{yapapi_version}{TEXT_COLOR_DEFAULT}\n"
            f"Using subnet: {TEXT_COLOR_YELLOW}{subnet_tag}{TEXT_COLOR_DEFAULT}, "
            f"payment driver: {TEXT_COLOR_YELLOW}{executor.driver}{TEXT_COLOR_DEFAULT}, "
            f"and network: {TEXT_COLOR_YELLOW}{executor.network}{TEXT_COLOR_DEFAULT}\n"
        )

        num_tasks = 0
        start_time = datetime.now()

        async for task in executor.submit(worker, [Task(data=frame) for frame in frames]):
            num_tasks += 1
            print(
                f"{TEXT_COLOR_CYAN}"
                f"Task computed: {task}, result: {task.result}, time: {task.running_time}"
                f"{TEXT_COLOR_DEFAULT}"
            )

        print(
            f"{TEXT_COLOR_CYAN}"
            f"{num_tasks} tasks computed, total time: {datetime.now() - start_time}"
            f"{TEXT_COLOR_DEFAULT}"
        )


if __name__ == "__main__":
    parser = build_parser("Render a Blender scene")
    parser.set_defaults(log_file="blender-yapapi.log")
    args = parser.parse_args()

    # This is only required when running on Windows with Python prior to 3.8:
    windows_event_loop_fix()

    enable_default_logger(
        log_file=args.log_file,
        debug_activity_api=True,
        debug_market_api=True,
        debug_payment_api=True,
    )

    loop = asyncio.get_event_loop()
    task = loop.create_task(
        main(subnet_tag=args.subnet_tag, driver=args.driver, network=args.network)
    )

    try:
        loop.run_until_complete(task)
    except NoPaymentAccountError as e:
        handbook_url = (
            "https://handbook.golem.network/requestor-tutorials/"
            "flash-tutorial-of-requestor-development"
        )
        print(
            f"{TEXT_COLOR_RED}"
            f"No payment account initialized for driver `{e.required_driver}` "
            f"and network `{e.required_network}`.\n\n"
            f"See {handbook_url} on how to initialize payment accounts for a requestor node."
            f"{TEXT_COLOR_DEFAULT}"
        )
    except KeyboardInterrupt:
        print(
            f"{TEXT_COLOR_YELLOW}"
            "Shutting down gracefully, please wait a short while "
            "or press Ctrl+C to exit immediately..."
            f"{TEXT_COLOR_DEFAULT}"
        )
        task.cancel()
        try:
            loop.run_until_complete(task)
            print(
                f"{TEXT_COLOR_YELLOW}Shutdown completed, thank you for waiting!{TEXT_COLOR_DEFAULT}"
            )
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass