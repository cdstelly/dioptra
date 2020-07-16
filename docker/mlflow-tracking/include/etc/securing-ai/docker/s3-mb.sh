#!/bin/bash

# Created by argbash-init v2.8.1
# ARG_OPTIONAL_SINGLE([endpoint-url],[],[Endpoint URL for S3 storage],[])
# ARG_POSITIONAL_SINGLE([bucket],[Bucket name],[])
# ARG_DEFAULTS_POS()
# ARGBASH_SET_INDENT([  ])
# ARG_HELP([Create bucket on S3 storage backend\n])"
# ARGBASH_GO()
# needed because of Argbash --> m4_ignore([
### START OF CODE GENERATED BY Argbash v2.8.1 one line above ###
# Argbash is a bash code generator used to get arguments parsing right.
# Argbash is FREE SOFTWARE, see https://argbash.io for more info


die()
{
  local _ret=$2
  test -n "$_ret" || _ret=1
  test "$_PRINT_HELP" = yes && print_help >&2
  echo "$1" >&2
  exit ${_ret}
}


begins_with_short_option()
{
  local first_option all_short_options='h'
  first_option="${1:0:1}"
  test "$all_short_options" = "${all_short_options/$first_option/}" && return 1 || return 0
}

# THE DEFAULTS INITIALIZATION - POSITIONALS
_positionals=()
_arg_bucket=
# THE DEFAULTS INITIALIZATION - OPTIONALS
_arg_endpoint_url=


print_help()
{
  printf '%s\n' "Create bucket on S3 storage backend
"
  printf 'Usage: %s [--endpoint-url <arg>] [-h|--help] <bucket>\n' "$0"
  printf '\t%s\n' "<bucket>: Bucket name"
  printf '\t%s\n' "--endpoint-url: Endpoint URL for S3 storage (no default)"
  printf '\t%s\n' "-h, --help: Prints help"
}


parse_commandline()
{
  _positionals_count=0
  while test $# -gt 0
  do
    _key="$1"
    case "$_key" in
      --endpoint-url)
        test $# -lt 2 && die "Missing value for the optional argument '$_key'." 1
        _arg_endpoint_url="$2"
        shift
        ;;
      --endpoint-url=*)
        _arg_endpoint_url="${_key##--endpoint-url=}"
        ;;
      -h|--help)
        print_help
        exit 0
        ;;
      -h*)
        print_help
        exit 0
        ;;
      *)
        _last_positional="$1"
        _positionals+=("$_last_positional")
        _positionals_count=$((_positionals_count + 1))
        ;;
    esac
    shift
  done
}


handle_passed_args_count()
{
  local _required_args_string="'bucket'"
  test "${_positionals_count}" -ge 1 || _PRINT_HELP=yes die "FATAL ERROR: Not enough positional arguments - we require exactly 1 (namely: $_required_args_string), but got only ${_positionals_count}." 1
  test "${_positionals_count}" -le 1 || _PRINT_HELP=yes die "FATAL ERROR: There were spurious positional arguments --- we expect exactly 1 (namely: $_required_args_string), but got ${_positionals_count} (the last one was: '${_last_positional}')." 1
}


assign_positional_args()
{
  local _positional_name _shift_for=$1
  _positional_names="_arg_bucket "

  shift "$_shift_for"
  for _positional_name in ${_positional_names}
  do
    test $# -gt 0 || break
    eval "$_positional_name=\${1}" || die "Error during argument parsing, possibly an Argbash bug." 1
    shift
  done
}

parse_commandline "$@"
handle_passed_args_count
assign_positional_args 1 "${_positionals[@]}"

# OTHER STUFF GENERATED BY Argbash

### END OF CODE GENERATED BY Argbash (sortof) ### ])
# [ <-- needed because of Argbash

shopt -s extglob
set -euo pipefail

###########################################################################################
# Global parameters
###########################################################################################

readonly bucket="${_arg_bucket}"
readonly endpoint_url="${_arg_endpoint_url}"
readonly logname="S3 Make Bucket"

###########################################################################################
# Check if bucket already exists
#
# Globals:
#   bucket
#   endpoint_url
# Arguments:
#   None
# Returns:
#   None
###########################################################################################

s3_bucket_exists() {
  if [[ ! -z ${endpoint_url} ]]; then
    aws --endpoint-url ${endpoint_url} s3api head-bucket --bucket ${bucket}
  else
    aws s3api head-bucket --bucket ${bucket}
  fi
}

###########################################################################################
# Create bucket on S3 storage
#
# Globals:
#   bucket
#   endpoint_url
#   logname
# Arguments:
#   None
# Returns:
#   None
###########################################################################################

s3_mb() {
  echo "${logname}: Creating bucket s3://${bucket}"

  if [[ ! -z ${endpoint_url} ]]; then
    echo "${logname}: custom endpoint URL ${endpoint_url}"

    [[ -z $(s3_bucket_exists 2>&1) ]] || aws --endpoint-url ${endpoint_url} s3 mb s3://${bucket}
  else
    echo "${logname}: default endpoint URL"

    [[ -z $(s3_bucket_exists 2>&1) ]] || aws s3 mb s3://${bucket}
  fi
}

###########################################################################################
# Main script
###########################################################################################

s3_mb
# ] <-- needed because of Argbash
