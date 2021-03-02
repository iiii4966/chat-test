ckage main

import (
	"flag"
	"golang.org/x/net/websocket"
	"log"
	"net/http"
	"sync"
)

/*

Simple chat using net/websocket
Do not use...

*/

type conns []*websocket.Conn

var lock = &sync.Mutex{}

func (c *conns) add(conn *websocket.Conn) {
	lock.Lock()
	defer lock.Unlock()
	*c = append(*c, conn)
}

func (c *conns) subtract(conn *websocket.Conn) {
	lock.Lock()
	defer lock.Unlock()
	for i := 0; i < len(*c); i++ {
		if (*c)[i] == conn {
			*c = append((*c)[:i], (*c)[i+1:]...)
			log.Print(*c)
			break
		}
	}
}

var users conns

func recv(messageChan chan []byte, conn *websocket.Conn) error {
	message := make([]byte, 1024)
	n, err := conn.Read(message)
	if err != nil {
		return err
	}
	messageChan <- message[:n]
	return nil
}

func broadcast(messageChan chan []byte) {
	for {
		select {
		case message := <-messageChan:
			for _, user := range users {
				_, err := user.Write(message)
				if err != nil {
					log.Println(err)
					if err := user.Close(); err != nil {
						log.Println(err)
					}
					users.subtract(user)
				}
			}
		}
	}
}

func main() {

	host := flag.String("host", "127.0.0.1", "server host")
	port := flag.String("port", "9000", "server port")

	flag.Parse()

	messageChan := make(chan []byte, 10)
	go broadcast(messageChan)

	mux := http.NewServeMux()
	mux.Handle("/", websocket.Handler(func(conn *websocket.Conn) {
		users.add(conn)
		for {
			err := recv(messageChan, conn)
			if err != nil {
				_ = conn.Close()
				break
			}
		}
		users.subtract(conn)
	}))

	url := *host + ":" + *port
	log.Printf("server run %s", url)
	log.Fatal(http.ListenAndServe(url, mux))
}

