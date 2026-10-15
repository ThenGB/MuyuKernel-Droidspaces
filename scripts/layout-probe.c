#include <linux/sched.h>
#include <linux/sched/signal.h>
#include <linux/sched/user.h>
#include <linux/mm_types.h>
#include <linux/cred.h>
#include <linux/nsproxy.h>
#include <linux/fs.h>
struct task_struct probe_task;
struct signal_struct probe_signal;
struct user_struct probe_user;
struct mm_struct probe_mm;
struct cred probe_cred;
struct nsproxy probe_nsproxy;
struct inode probe_inode;
struct file probe_file;
