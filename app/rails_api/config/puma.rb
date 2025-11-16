# Puma configuration file

# Specifies the `port` that Puma will listen on to receive requests
port ENV.fetch("PORT", 3000)

# Specifies the `environment` that Puma will run in
environment ENV.fetch("RAILS_ENV", "development")

# Specifies the number of `workers` to boot in clustered mode
workers ENV.fetch("WEB_CONCURRENCY", 2)

# Use the `preload_app!` method when specifying a `workers` number
preload_app!

# Allow puma to be restarted by `bin/rails restart` command
plugin :tmp_restart

# Specify the PID file
pidfile ENV.fetch("PIDFILE", "tmp/pids/server.pid")

# Daemonize the server
# daemonize false

# Number of threads
threads_count = ENV.fetch("RAILS_MAX_THREADS", 5)
threads threads_count, threads_count

# Bind to specific address
bind "tcp://0.0.0.0:#{ENV.fetch('PORT', 3000)}"

# Health check endpoint
on_worker_boot do
  ActiveRecord::Base.establish_connection if defined?(ActiveRecord)
end
