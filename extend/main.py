from os.path import join

from SCons.Script import (
    AlwaysBuild, Builder, COMMAND_LINE_TARGETS, Default, DefaultEnvironment)


env = DefaultEnvironment()
platform = env.PioPlatform()


env.Replace(
    AR="arm-none-eabi-ar",
    AS="arm-none-eabi-as",
    CC="arm-none-eabi-gcc",
    GDB="arm-none-eabi-gdb",
    CXX="arm-none-eabi-g++",
    OBJCOPY="arm-none-eabi-objcopy",
    RANLIB="arm-none-eabi-gcc-ranlib",
    SIZETOOL="arm-none-eabi-size",

    ARFLAGS=["rcs"],

    SIZEPROGREGEXP=r"^(?:\.text|\.data|\.rodata|\.text.align|\.ARM.exidx|\.cybootloader)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.noinit)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)

env.Append(
    BUILDERS=dict(
        ElfToHex=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".hex"
        ),
        GenerateCyacd=Builder(
            action=env.VerboseAction(" ".join([
                '"%s"' % join(platform.get_package_dir(
                    "tool-cubecellelftool") or "", "CubeCellelftool"),
                "$OBJCOPY",
                "${SOURCES[0]}",
                "${SOURCES[1]}",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".cyacd"
        )
    )
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_hex = join("$BUILD_DIR", "${PROGNAME}.hex")
    target_firm = join("$BUILD_DIR", "${PROGNAME}.cyacd")
else:
    target_elf = env.BuildProgram()
    target_hex = env.ElfToHex(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_firm = env.GenerateCyacd(
        join("$BUILD_DIR", "${PROGNAME}"), [target_elf, target_hex])

AlwaysBuild(env.Alias("nobuild", target_firm))
target_buildprog = env.Alias("buildprog", target_firm, target_firm)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload by default .hex file
#

upload_protocol = env.subst("$UPLOAD_PROTOCOL")

if upload_protocol == "serial":
    env.Replace(
        UPLOADER="CubeCellflash",
        UPLOADERFLAGS=[
            "-serial", '"$UPLOAD_PORT"'
        ],
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS $SOURCES"
    )
    upload_actions = [
        env.VerboseAction(env.AutodetectUploadPort, "Looking for upload port..."),
        env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")
    ]

elif upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

AlwaysBuild(env.Alias("upload", target_firm, upload_actions))

#
# Target: Define targets
#

Default([target_buildprog, target_size])
